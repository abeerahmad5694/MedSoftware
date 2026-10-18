from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.myaccounts.models import Accounts
from apps.diary.models import DiaryHistory, DiaryItem


ZERO = Decimal("0.00")
MONEY_KINDS = {DiaryItem.Kind.PAYABLE, DiaryItem.Kind.RECEIVABLE}


class DiaryServiceError(ValueError):
    """A user-correctable diary operation error."""


def parse_date(value, field_name="Date", required=False):
    if value in (None, ""):
        if required:
            raise DiaryServiceError(f"{field_name} is required.")
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DiaryServiceError(f"Enter a valid {field_name.lower()}.")


def parse_money(value, field_name="Amount", required=True):
    if value in (None, ""):
        if required:
            raise DiaryServiceError(f"{field_name} is required.")
        return None
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise DiaryServiceError(f"Enter a valid {field_name.lower()}.")
    if not amount.is_finite():
        raise DiaryServiceError(f"Enter a valid {field_name.lower()}.")
    return amount


def parse_positive_int(value, field_name, allow_blank=True):
    if value in (None, ""):
        if allow_blank:
            return None
        raise DiaryServiceError(f"{field_name} is required.")
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise DiaryServiceError(f"Enter a valid {field_name.lower()}.")
    if parsed < 1:
        raise DiaryServiceError(f"{field_name} must be at least 1.")
    return parsed


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def validate_account_code(acc_code, company_id=None):
    if acc_code in (None, ""):
        raise DiaryServiceError("Select an account.")
    try:
        code = int(acc_code)
    except (TypeError, ValueError):
        raise DiaryServiceError("Select a valid account.")

    accounts = Accounts.objects.filter(ACC_CODE=code, TYPE__iexact="Detail")
    if company_id is not None:
        accounts = accounts.filter(COMPANY_id=company_id)
    if not accounts.exists():
        raise DiaryServiceError("The selected account was not found for this company.")
    return code


def record_history(
    item,
    action,
    *,
    amount=None,
    reason="",
    note="",
    old_due_date=None,
    new_due_date=None,
    old_amount=None,
    new_amount=None,
    balance_after=None,
):
    return DiaryHistory.objects.create(
        dairyitem=item,
        action=action,
        amount=amount,
        reason=reason or "",
        note=(note or "").strip(),
        old_due_date=old_due_date,
        new_due_date=new_due_date,
        old_amount=old_amount,
        new_amount=new_amount,
        balance_after=balance_after,
    )


def _create_next_repeat(item):
    """Create one next occurrence after this reminder is fully cleared."""
    if item.kind not in MONEY_KINDS or not item.repeat_every_days or not item.amount:
        return None

    next_date = timezone.now().date() + timedelta(days=item.repeat_every_days)
    next_item = DiaryItem.objects.create(
        kind=item.kind,
        title=item.title,
        details=item.details,
        acc_code=item.acc_code,
        scheduled_date=next_date,
        original_due_date=next_date,
        amount=item.amount,
        remaining_amount=item.amount,
        status=DiaryItem.Status.OPEN,
        repeat_every_days=item.repeat_every_days,
        company_id=item.company_id,
        branch_id=item.branch_id,
    )
    record_history(
        next_item,
        DiaryHistory.Action.CREATED,
        amount=next_item.amount,
        balance_after=next_item.remaining_amount,
        new_due_date=next_date,
        note=f"Next reminder in the {item.repeat_every_days}-day repeat schedule.",
    )
    return next_item


@transaction.atomic
def create_diary_item(payload, *, company_id=None, branch_id=None):
    kind = str(payload.get("kind", "")).strip().upper()
    if kind not in DiaryItem.Kind.values:
        raise DiaryServiceError("Select a valid diary entry type.")

    title = str(payload.get("title", "")).strip()
    details = str(payload.get("details", "")).strip()
    scheduled_date = parse_date(payload.get("scheduled_date"), "Date", required=True)
    follow_up_date = parse_date(payload.get("follow_up_date"), "Follow-up date")
    pinned = parse_bool(payload.get("pinned"))

    acc_code = None
    amount = None
    remaining = None
    original_due_date = None
    repeat_every_days = None

    if kind in MONEY_KINDS:
        acc_code = validate_account_code(payload.get("acc_code"), company_id)
        amount = parse_money(payload.get("amount"), required=True)
        if amount <= ZERO:
            raise DiaryServiceError("Reminder amount must be greater than zero.")
        remaining = amount
        original_due_date = scheduled_date
        repeat_every_days = parse_positive_int(
            payload.get("repeat_every_days"), "Repeat interval"
        )
    else:
        pinned = pinned if kind == DiaryItem.Kind.NOTE else False
        follow_up_date = follow_up_date if kind in {DiaryItem.Kind.NOTE, DiaryItem.Kind.TASK} else None
        if not title and not details:
            raise DiaryServiceError("Enter a title or note.")

    item = DiaryItem.objects.create(
        kind=kind,
        title=title,
        details=details,
        acc_code=acc_code,
        scheduled_date=scheduled_date,
        original_due_date=original_due_date,
        amount=amount,
        remaining_amount=remaining,
        status=DiaryItem.Status.OPEN,
        pinned=pinned,
        follow_up_date=follow_up_date,
        repeat_every_days=repeat_every_days,
        company_id=company_id,
        branch_id=branch_id,
    )
    record_history(
        item,
        DiaryHistory.Action.CREATED,
        amount=amount,
        balance_after=remaining,
        new_due_date=scheduled_date,
        note="Diary entry created.",
    )
    return item


@transaction.atomic
def update_diary_item(item, payload, *, company_id=None):
    item = DiaryItem.objects.select_for_update().get(pk=item.pk)
    if item.deleted_at:
        raise DiaryServiceError("This diary entry has been deleted.")
    if item.kind in MONEY_KINDS and item.status != DiaryItem.Status.OPEN:
        raise DiaryServiceError("A completed reminder cannot be edited.")

    changed = False
    old_due_date = item.scheduled_date
    old_amount = item.amount

    if "title" in payload:
        item.title = str(payload.get("title") or "").strip()
        changed = True
    if "details" in payload:
        item.details = str(payload.get("details") or "").strip()
        changed = True
    if "scheduled_date" in payload:
        new_date = parse_date(payload.get("scheduled_date"), "Date", required=True)
        if new_date != item.scheduled_date:
            item.scheduled_date = new_date
            changed = True
    if "pinned" in payload:
        item.pinned = parse_bool(payload.get("pinned")) if item.kind == DiaryItem.Kind.NOTE else False
        changed = True
    if "follow_up_date" in payload:
        item.follow_up_date = (
            parse_date(payload.get("follow_up_date"), "Follow-up date")
            if item.kind in {DiaryItem.Kind.NOTE, DiaryItem.Kind.TASK} else None
        )
        changed = True

    if item.kind in MONEY_KINDS:
        if "acc_code" in payload:
            item.acc_code = validate_account_code(payload.get("acc_code"), company_id)
            changed = True
        if "amount" in payload:
            new_amount = parse_money(payload.get("amount"), required=True)
            if new_amount <= ZERO:
                raise DiaryServiceError("Reminder amount must be greater than zero.")
            already_applied = (item.amount or ZERO) - (item.remaining_amount or ZERO)
            if new_amount < already_applied:
                raise DiaryServiceError("Amount cannot be less than payments already recorded.")
            if new_amount != item.amount:
                item.amount = new_amount
                item.remaining_amount = new_amount - already_applied
                record_history(
                    item,
                    DiaryHistory.Action.ADJUSTED,
                    old_amount=old_amount,
                    new_amount=new_amount,
                    balance_after=item.remaining_amount,
                    note="Reminder amount updated.",
                )
                changed = True
        if "repeat_every_days" in payload:
            item.repeat_every_days = parse_positive_int(
                payload.get("repeat_every_days"), "Repeat interval"
            )
            changed = True

    item.save()
    if changed:
        date_changed = old_due_date != item.scheduled_date
        action = (
            DiaryHistory.Action.EXTENDED
            if date_changed and item.kind in MONEY_KINDS and item.scheduled_date > old_due_date
            else DiaryHistory.Action.UPDATED
        )
        record_history(
            item,
            action,
            old_due_date=old_due_date if date_changed else None,
            new_due_date=item.scheduled_date if date_changed else None,
            balance_after=item.remaining_amount,
            note="Due date extended." if action == DiaryHistory.Action.EXTENDED else "Diary entry updated.",
        )
    return item


@transaction.atomic
def apply_diary_action(item, payload):
    item = DiaryItem.objects.select_for_update().get(pk=item.pk)
    if item.deleted_at:
        raise DiaryServiceError("This diary entry has been deleted.")
    if item.status != DiaryItem.Status.OPEN:
        raise DiaryServiceError("This diary entry is already closed.")

    action = str(payload.get("action", "")).strip().lower()
    note = str(payload.get("note", "")).strip()

    if item.kind == DiaryItem.Kind.TASK:
        if action != "done":
            raise DiaryServiceError("Tasks can only be marked complete.")
        item.status = DiaryItem.Status.DONE
        item.save(update_fields=["status", "updated_at"])
        record_history(item, DiaryHistory.Action.TASK_DONE, note=note, balance_after=None)
        return item

    if item.kind not in MONEY_KINDS:
        raise DiaryServiceError("This diary entry does not have payment actions.")

    remaining = item.remaining_amount or ZERO
    if remaining <= ZERO:
        raise DiaryServiceError("There is no remaining balance on this reminder.")

    close_repeat = False
    if action == "full":
        if item.kind == DiaryItem.Kind.PAYABLE:
            item.status = DiaryItem.Status.PAID
            history_action = DiaryHistory.Action.PAYMENT_FULL
        else:
            item.status = DiaryItem.Status.RECEIVED
            history_action = DiaryHistory.Action.RECEIPT_FULL
        applied_amount = remaining
        item.remaining_amount = ZERO
        close_repeat = True
        item.save(update_fields=["status", "remaining_amount", "updated_at"])
        record_history(
            item,
            history_action,
            amount=applied_amount,
            note=note,
            balance_after=ZERO,
        )

    elif action == "partial":
        applied_amount = parse_money(payload.get("amount"), field_name="Payment amount")
        if applied_amount <= ZERO or applied_amount >= remaining:
            if applied_amount == remaining:
                raise DiaryServiceError("Use the full payment action when the full balance is paid.")
            raise DiaryServiceError("Partial amount must be greater than zero and less than the remaining balance.")
        item.remaining_amount = remaining - applied_amount
        if item.kind == DiaryItem.Kind.PAYABLE:
            history_action = DiaryHistory.Action.PAYMENT_PARTIAL
        else:
            history_action = DiaryHistory.Action.RECEIPT_PARTIAL
        item.save(update_fields=["remaining_amount", "updated_at"])
        record_history(
            item,
            history_action,
            amount=applied_amount,
            note=note,
            balance_after=item.remaining_amount,
        )
        _set_next_date_if_requested(item, payload, note)

    elif action == "extend":
        _extend_item(item, payload.get("next_date"), note)

    elif action == "settle":
        applied_amount = parse_money(
            payload.get("amount"), field_name="Settlement amount", required=False
        )
        if applied_amount is None:
            applied_amount = remaining
        if applied_amount <= ZERO or applied_amount > remaining:
            raise DiaryServiceError("Settlement amount must be greater than zero and no more than the remaining balance.")

        reason = str(payload.get("reason", "")).strip().upper()
        if reason not in DiaryHistory.SettlementReason.values:
            raise DiaryServiceError("Select a settlement reason.")

        item.remaining_amount = remaining - applied_amount
        if item.remaining_amount == ZERO:
            item.status = DiaryItem.Status.SETTLED
            close_repeat = True
        item.save(update_fields=["remaining_amount", "status", "updated_at"])
        record_history(
            item,
            DiaryHistory.Action.SETTLED,
            amount=applied_amount,
            reason=reason,
            note=note,
            balance_after=item.remaining_amount,
        )
        if item.status == DiaryItem.Status.OPEN:
            _set_next_date_if_requested(item, payload, note)

    else:
        raise DiaryServiceError("Select a valid action.")

    if close_repeat:
        _create_next_repeat(item)
    return item


def _extend_item(item, new_date_value, note=""):
    new_date = parse_date(new_date_value, "Next reminder date", required=True)
    old_date = item.scheduled_date
    if new_date <= old_date or new_date < timezone.now().date():
        raise DiaryServiceError("Choose a reminder date after the current due date and not in the past.")
    item.scheduled_date = new_date
    item.save(update_fields=["scheduled_date", "updated_at"])
    record_history(
        item,
        DiaryHistory.Action.EXTENDED,
        note=note,
        old_due_date=old_date,
        new_due_date=new_date,
        balance_after=item.remaining_amount,
    )


def _set_next_date_if_requested(item, payload, note=""):
    next_date_value = payload.get("next_date")
    if next_date_value in (None, ""):
        return
    new_date = parse_date(next_date_value, "Next reminder date", required=True)
    if new_date < timezone.now().date():
        raise DiaryServiceError("The next reminder date cannot be in the past.")
    old_date = item.scheduled_date
    if new_date == old_date:
        return
    item.scheduled_date = new_date
    item.save(update_fields=["scheduled_date", "updated_at"])
    record_history(
        item,
        DiaryHistory.Action.EXTENDED,
        note=note or "Next reminder date set for the remaining balance.",
        old_due_date=old_date,
        new_due_date=new_date,
        balance_after=item.remaining_amount,
    )


@transaction.atomic
def soft_delete_diary_item(item, note=""):
    item = DiaryItem.objects.select_for_update().get(pk=item.pk)
    if item.deleted_at:
        return item
    item.status = DiaryItem.Status.CANCELLED
    item.deleted_at = timezone.now()
    item.save(update_fields=["status", "deleted_at", "updated_at"])
    record_history(
        item,
        DiaryHistory.Action.DELETED,
        balance_after=item.remaining_amount,
        note=note or "Diary entry deleted or cancelled.",
    )
    return item
