# Initial schema for the diary and reminder module.

import django.db.models.deletion
from django.db import migrations, models


DIARY_PERMISSIONS = [
    ("View Diary & Reminders", "view_diary"),
    ("Create Diary Notes & Tasks", "create_diary_items"),
    ("Update Diary Entries", "update_diary_items"),
    ("Delete Diary Entries", "delete_diary_items"),
    ("Add Payable Reminders", "add_payable_reminders"),
    ("Add Receivable Reminders", "add_receivable_reminders"),
]


def create_diary_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    database = schema_editor.connection.alias
    for name, code in DIARY_PERMISSIONS:
        Permission.objects.using(database).get_or_create(
            code=code,
            defaults={"name": name, "module": "diary"},
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("configuration", "0012_companyconfiguration_stock_valuation_method"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiaryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("NOTE", "Note"), ("TASK", "Task / Schedule"), ("PAYABLE", "Payable reminder"), ("RECEIVABLE", "Receivable reminder")], db_index=True, max_length=12)),
                ("title", models.CharField(blank=True, max_length=160)),
                ("details", models.TextField(blank=True)),
                ("acc_code", models.IntegerField(blank=True, db_index=True, null=True)),
                ("scheduled_date", models.DateField(db_index=True)),
                ("original_due_date", models.DateField(blank=True, null=True)),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("remaining_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("DONE", "Done"), ("PAID", "Paid"), ("RECEIVED", "Received"), ("SETTLED", "Settled"), ("CANCELLED", "Cancelled")], db_index=True, default="OPEN", max_length=12)),
                ("pinned", models.BooleanField(default=False)),
                ("follow_up_date", models.DateField(blank=True, null=True)),
                ("repeat_every_days", models.PositiveIntegerField(blank=True, null=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="diary_items", to="configuration.branch")),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="diary_items", to="configuration.company")),
            ],
            options={
                "db_table": "diary_item",
                "ordering": ["scheduled_date", "id"],
            },
        ),
        migrations.CreateModel(
            name="DiaryHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("CREATED", "Created"), ("UPDATED", "Updated"), ("PAYMENT_PARTIAL", "Partial payment"), ("PAYMENT_FULL", "Fully paid"), ("RECEIPT_PARTIAL", "Partial receipt"), ("RECEIPT_FULL", "Fully received"), ("EXTENDED", "Due date extended"), ("SETTLED", "Settled / adjusted"), ("ADJUSTED", "Amount adjusted"), ("TASK_DONE", "Task completed"), ("DELETED", "Deleted")], db_index=True, max_length=20)),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("reason", models.CharField(blank=True, choices=[("DISCOUNT", "Discount"), ("ADJUSTMENT", "Adjustment"), ("RETURN", "Return"), ("BAD_DEBT", "Bad debt"), ("MUTUAL", "Mutual settlement"), ("OTHER", "Other")], max_length=20)),
                ("note", models.TextField(blank=True)),
                ("old_due_date", models.DateField(blank=True, null=True)),
                ("new_due_date", models.DateField(blank=True, null=True)),
                ("old_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("new_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("balance_after", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("dairyitem", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="history", to="diary.diaryitem")),
            ],
            options={
                "db_table": "diary_history",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="diaryitem",
            index=models.Index(fields=["company", "branch", "status", "scheduled_date"], name="diary_scope_due_idx"),
        ),
        migrations.AddIndex(
            model_name="diaryitem",
            index=models.Index(fields=["acc_code", "status"], name="diary_acc_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="diaryitem",
            constraint=models.CheckConstraint(condition=models.Q(("remaining_amount__gte", 0), ("remaining_amount__isnull", True), _connector="OR"), name="diary_remaining_nonnegative"),
        ),
        migrations.AddIndex(
            model_name="diaryhistory",
            index=models.Index(fields=["dairyitem", "created_at"], name="dairyhist_item_dt_idx"),
        ),
        migrations.RunPython(create_diary_permissions, migrations.RunPython.noop),
    ]
