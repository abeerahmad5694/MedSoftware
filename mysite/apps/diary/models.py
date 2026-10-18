from django.db import models
from django.db.models import Q


class DiaryItem(models.Model):
    class Kind(models.TextChoices):
        NOTE = "NOTE", "Note"
        TASK = "TASK", "Task / Schedule"
        PAYABLE = "PAYABLE", "Payable reminder"
        RECEIVABLE = "RECEIVABLE", "Receivable reminder"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        DONE = "DONE", "Done"
        PAID = "PAID", "Paid"
        RECEIVED = "RECEIVED", "Received"
        SETTLED = "SETTLED", "Settled"
        CANCELLED = "CANCELLED", "Cancelled"

    kind = models.CharField(max_length=12, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=160, blank=True)
    details = models.TextField(blank=True)

    # Keep the ERP account code as a scalar value; intentionally no Accounts FK.
    acc_code = models.IntegerField(null=True, blank=True, db_index=True)

    scheduled_date = models.DateField(db_index=True)
    original_due_date = models.DateField(null=True, blank=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    remaining_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    pinned = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    repeat_every_days = models.PositiveIntegerField(null=True, blank=True)

    # These are ERP scope fields, not account relations.
    company = models.ForeignKey(
        "configuration.Company",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="diary_items",
    )
    branch = models.ForeignKey(
        "configuration.Branch",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="diary_items",
    )

    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "diary_item"
        ordering = ["scheduled_date", "id"]
        indexes = [
            models.Index(
                fields=["company", "branch", "status", "scheduled_date"],
                name="diary_scope_due_idx",
            ),
            models.Index(
                fields=["acc_code", "status"],
                name="diary_acc_status_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(remaining_amount__gte=0) | Q(remaining_amount__isnull=True),
                name="diary_remaining_nonnegative",
            ),
        ]

    def __str__(self):
        return self.title or f"{self.get_kind_display()} #{self.pk}"


class DiaryHistory(models.Model):
    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        PAYMENT_PARTIAL = "PAYMENT_PARTIAL", "Partial payment"
        PAYMENT_FULL = "PAYMENT_FULL", "Fully paid"
        RECEIPT_PARTIAL = "RECEIPT_PARTIAL", "Partial receipt"
        RECEIPT_FULL = "RECEIPT_FULL", "Fully received"
        EXTENDED = "EXTENDED", "Due date extended"
        SETTLED = "SETTLED", "Settled / adjusted"
        ADJUSTED = "ADJUSTED", "Amount adjusted"
        TASK_DONE = "TASK_DONE", "Task completed"
        DELETED = "DELETED", "Deleted"

    class SettlementReason(models.TextChoices):
        DISCOUNT = "DISCOUNT", "Discount"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        RETURN = "RETURN", "Return"
        BAD_DEBT = "BAD_DEBT", "Bad debt"
        MUTUAL = "MUTUAL", "Mutual settlement"
        OTHER = "OTHER", "Other"

    # The public field name is intentionally `dairyitem`, as requested.
    dairyitem = models.ForeignKey(
        DiaryItem,
        on_delete=models.PROTECT,
        related_name="history",
    )
    action = models.CharField(max_length=20, choices=Action.choices, db_index=True)
    amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    reason = models.CharField(
        max_length=20,
        choices=SettlementReason.choices,
        blank=True,
    )
    note = models.TextField(blank=True)
    old_due_date = models.DateField(null=True, blank=True)
    new_due_date = models.DateField(null=True, blank=True)
    old_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    new_amount = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    balance_after = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "diary_history"
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(
                fields=["dairyitem", "created_at"],
                name="dairyhist_item_dt_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_action_display()} — diary item {self.dairyitem_id}"
