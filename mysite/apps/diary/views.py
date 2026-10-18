import json
from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date as parse_query_date
from django.views.decorators.http import require_GET, require_POST

from apps.diary.models import DiaryHistory, DiaryItem
from apps.diary.services import (
    DiaryServiceError,
    apply_diary_action,
    create_diary_item,
    soft_delete_diary_item,
    update_diary_item,
)
from apps.myaccounts.models import Accounts
from apps.myledger.services.helpers import get_user_perms


MONEY_KINDS = (DiaryItem.Kind.PAYABLE, DiaryItem.Kind.RECEIVABLE)
CLOSED_ACTIONS = {
    DiaryHistory.Action.PAYMENT_FULL,
    DiaryHistory.Action.RECEIPT_FULL,
    DiaryHistory.Action.SETTLED,
}
ZERO = Decimal("0.00")


def _has_permission(request, code):
    try:
        allowed, _message = get_user_perms(request, code)
        return bool(allowed)
    except Exception:
        return False


def _user_scope(request):
    profile = getattr(request.user, "userprofile", None)
    if profile and profile.company_id:
        return profile.company_id, profile.branch_id
    if getattr(request.user, "is_superuser", False):
        return None, None
    return None, None


def _scoped_items(request):
    queryset = DiaryItem.objects.all()
    company_id, branch_id = _user_scope(request)
    if company_id is not None:
        queryset = queryset.filter(company_id=company_id)
        if branch_id is not None:
            queryset = queryset.filter(branch_id=branch_id)
        return queryset
    if getattr(request.user, "is_superuser", False):
        return queryset
    return queryset.none()


def _scope_for_create(request):
    company_id, branch_id = _user_scope(request)
    if company_id is None and not getattr(request.user, "is_superuser", False):
        raise DiaryServiceError("Your user profile must have a company assigned.")
    return company_id, branch_id


def _json_payload(request):
    try:
        value = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DiaryServiceError("Invalid request data.")
    if not isinstance(value, dict):
        raise DiaryServiceError("Invalid request data.")
    return value


def _error(message, status=400):
    return JsonResponse({"success": False, "message": str(message)}, status=status)


def _account_names(request, codes):
    codes = {int(code) for code in codes if code not in (None, "")}
    if not codes:
        return {}
    accounts = Accounts.objects.filter(ACC_CODE__in=codes)
    company_id, _branch_id = _user_scope(request)
    if company_id is not None:
        accounts = accounts.filter(COMPANY_id=company_id)
    return {
        row["ACC_CODE"]: (row["ACC_NAME"] or "").strip()
        for row in accounts.values("ACC_CODE", "ACC_NAME")
    }


def _attach_account_names(request, items):
    names = _account_names(request, [item.acc_code for item in items])
    for item in items:
        item.account_name = names.get(item.acc_code) or (
            f"Account {item.acc_code}" if item.acc_code else ""
        )
    return items


def _item_json(request, item):
    account_name = _account_names(request, [item.acc_code]).get(item.acc_code, "")
    return {
        "id": item.pk,
        "kind": item.kind,
        "kind_label": item.get_kind_display(),
        "title": item.title,
        "details": item.details,
        "acc_code": item.acc_code,
        "account_name": account_name,
        "scheduled_date": item.scheduled_date.isoformat() if item.scheduled_date else "",
        "original_due_date": item.original_due_date.isoformat() if item.original_due_date else "",
        "amount": str(item.amount) if item.amount is not None else "",
        "remaining_amount": str(item.remaining_amount) if item.remaining_amount is not None else "",
        "status": item.status,
        "pinned": item.pinned,
        "follow_up_date": item.follow_up_date.isoformat() if item.follow_up_date else "",
        "repeat_every_days": item.repeat_every_days or "",
    }


def _summary(queryset, today):
    open_reminders = queryset.filter(
        kind__in=MONEY_KINDS,
        status=DiaryItem.Status.OPEN,
        remaining_amount__gt=ZERO,
    )
    today_rows = open_reminders.filter(scheduled_date=today)
    overdue_rows = open_reminders.filter(scheduled_date__lt=today)
    upcoming_rows = open_reminders.filter(scheduled_date__gt=today)

    def amount(rows):
        return rows.aggregate(total=Sum("remaining_amount"))["total"] or ZERO

    return {
        "today_count": today_rows.count(),
        "today_amount": amount(today_rows),
        "overdue_count": overdue_rows.count(),
        "overdue_amount": amount(overdue_rows),
        "upcoming_count": upcoming_rows.count(),
        "upcoming_amount": amount(upcoming_rows),
    }


def _delay_report(request, queryset, today):
    money_items = list(
        queryset.filter(kind__in=MONEY_KINDS)
        .exclude(status=DiaryItem.Status.CANCELLED)
        .prefetch_related("history")
        .order_by("acc_code", "original_due_date", "id")
    )
    account_names = _account_names(request, [item.acc_code for item in money_items])
    groups = defaultdict(
        lambda: {
            "acc_code": None,
            "account_name": "",
            "overdue_count": 0,
            "overdue_amount": ZERO,
            "open_amount": ZERO,
            "extension_count": 0,
            "late_closed_count": 0,
            "late_days_total": 0,
            "late_days_average": 0,
        }
    )

    for item in money_items:
        if item.acc_code is None:
            continue
        row = groups[item.acc_code]
        row["acc_code"] = item.acc_code
        row["account_name"] = account_names.get(item.acc_code) or f"Account {item.acc_code}"

        if item.status == DiaryItem.Status.OPEN:
            row["open_amount"] += item.remaining_amount or ZERO
            if item.scheduled_date < today:
                row["overdue_count"] += 1
                row["overdue_amount"] += item.remaining_amount or ZERO

        for event in item.history.all():
            if event.action == DiaryHistory.Action.EXTENDED:
                row["extension_count"] += 1

        if item.status in {
            DiaryItem.Status.PAID,
            DiaryItem.Status.RECEIVED,
            DiaryItem.Status.SETTLED,
        } and item.original_due_date:
            closing_events = [
                event for event in item.history.all()
                if event.action in CLOSED_ACTIONS and event.balance_after == ZERO
            ]
            if closing_events:
                closed_on = closing_events[-1].created_at.date()
                days_late = (closed_on - item.original_due_date).days
                if days_late > 0:
                    row["late_closed_count"] += 1
                    row["late_days_total"] += days_late

    rows = list(groups.values())
    for row in rows:
        if row["late_closed_count"]:
            row["late_days_average"] = round(
                row["late_days_total"] / row["late_closed_count"], 1
            )
    rows.sort(
        key=lambda row: (
            row["overdue_amount"],
            row["extension_count"],
            row["late_days_average"],
        ),
        reverse=True,
    )
    return rows


def diary_home(request):
    if not _has_permission(request, "view_diary"):
        return redirect("page_not_found")

    today = timezone.now().date()
    active = _scoped_items(request).filter(deleted_at__isnull=True)
    summary = _summary(active, today)
    selected_view = request.GET.get("view", "today")
    valid_views = {"today", "overdue", "upcoming", "diary", "report"}
    if selected_view not in valid_views:
        selected_view = "today"

    from_date_value = request.GET.get("from_date", "").strip()
    to_date_value = request.GET.get("to_date", "").strip()
    try:
        from_date = parse_query_date(from_date_value) if from_date_value else None
    except ValueError:
        from_date = None
    try:
        to_date = parse_query_date(to_date_value) if to_date_value else None
    except ValueError:
        to_date = None

    date_filter_errors = []
    if selected_view == "diary":
        if from_date_value and from_date is None:
            date_filter_errors.append("Enter a valid from date.")
        if to_date_value and to_date is None:
            date_filter_errors.append("Enter a valid to date.")
        if from_date and to_date and from_date > to_date:
            date_filter_errors.append("The from date must be on or before the to date.")
    date_filter_error = " ".join(date_filter_errors)

    report_rows = []
    if selected_view == "report":
        report_rows = _delay_report(request, active, today)
        items = []
    else:
        items_query = active
        if selected_view == "today":
            items_query = items_query.filter(status=DiaryItem.Status.OPEN).filter(
                Q(scheduled_date=today) | Q(follow_up_date=today)
            )
        elif selected_view == "overdue":
            items_query = items_query.filter(status=DiaryItem.Status.OPEN).filter(
                Q(
                    kind__in=MONEY_KINDS,
                    remaining_amount__gt=ZERO,
                    scheduled_date__lt=today,
                )
                | Q(kind=DiaryItem.Kind.TASK, scheduled_date__lt=today)
                | Q(kind__in=(DiaryItem.Kind.NOTE, DiaryItem.Kind.TASK), follow_up_date__lt=today)
            )
        elif selected_view == "upcoming":
            items_query = items_query.filter(status=DiaryItem.Status.OPEN).filter(
                Q(kind__in=MONEY_KINDS, remaining_amount__gt=ZERO, scheduled_date__gt=today)
                | Q(kind=DiaryItem.Kind.TASK, scheduled_date__gt=today)
                | Q(kind=DiaryItem.Kind.NOTE, follow_up_date__gt=today)
                | Q(kind=DiaryItem.Kind.TASK, follow_up_date__gt=today)
            )
        else:
            # The diary view includes open entries and completed items for context.
            items_query = items_query.exclude(status=DiaryItem.Status.CANCELLED)
            if not date_filter_error:
                if from_date:
                    items_query = items_query.filter(scheduled_date__gte=from_date)
                if to_date:
                    items_query = items_query.filter(scheduled_date__lte=to_date)

        kind_filter = request.GET.get("kind", "").upper()
        if kind_filter in DiaryItem.Kind.values:
            items_query = items_query.filter(kind=kind_filter)

        items = list(items_query.order_by("-pinned", "scheduled_date", "id")[:400])
        _attach_account_names(request, items)

    permissions = {
        "can_create_note": _has_permission(request, "create_diary_items"),
        "can_add_payable": _has_permission(request, "add_payable_reminders"),
        "can_add_receivable": _has_permission(request, "add_receivable_reminders"),
        "can_update": _has_permission(request, "update_diary_items"),
        "can_delete": _has_permission(request, "delete_diary_items"),
    }
    permissions["can_create_any"] = any(
        permissions[key] for key in ("can_create_note", "can_add_payable", "can_add_receivable")
    )

    return render(
        request,
        "diary/diary.html",
        {
            "items": items,
            "selected_view": selected_view,
            "kind_filter": request.GET.get("kind", ""),
            "from_date_value": from_date_value,
            "to_date_value": to_date_value,
            "date_filter_error": date_filter_error,
            "report_rows": report_rows,
            "summary": summary,
            "today": today,
            **permissions,
        },
    )


@require_GET
def api_item(request, item_id):
    if not _has_permission(request, "view_diary"):
        return _error("You do not have permission to view diary entries.", status=403)
    item = get_object_or_404(_scoped_items(request).filter(deleted_at__isnull=True), pk=item_id)
    return JsonResponse({"success": True, "item": _item_json(request, item)})


@require_GET
def api_history(request, item_id):
    if not _has_permission(request, "view_diary"):
        return _error("You do not have permission to view diary history.", status=403)
    item = get_object_or_404(_scoped_items(request), pk=item_id)
    history = []
    for event in item.history.all().order_by("created_at", "id"):
        history.append({
            "action": event.get_action_display(),
            "amount": str(event.amount) if event.amount is not None else "",
            "reason": event.get_reason_display() if event.reason else "",
            "note": event.note,
            "old_due_date": event.old_due_date.isoformat() if event.old_due_date else "",
            "new_due_date": event.new_due_date.isoformat() if event.new_due_date else "",
            "old_amount": str(event.old_amount) if event.old_amount is not None else "",
            "new_amount": str(event.new_amount) if event.new_amount is not None else "",
            "balance_after": str(event.balance_after) if event.balance_after is not None else "",
            "created_at": event.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return JsonResponse({"success": True, "history": history})


@require_POST
def api_create(request):
    try:
        payload = _json_payload(request)
        kind = str(payload.get("kind", "")).strip().upper()
        if kind == DiaryItem.Kind.PAYABLE:
            permission = "add_payable_reminders"
        elif kind == DiaryItem.Kind.RECEIVABLE:
            permission = "add_receivable_reminders"
        else:
            permission = "create_diary_items"
        if not _has_permission(request, permission):
            return _error("You do not have permission to create this entry.", status=403)
        company_id, branch_id = _scope_for_create(request)
        item = create_diary_item(payload, company_id=company_id, branch_id=branch_id)
        return JsonResponse({"success": True, "message": "Diary entry saved.", "id": item.pk})
    except DiaryServiceError as exc:
        return _error(exc)
    except Http404:
        raise
    except Exception:
        return _error("Unable to save this diary entry.", status=500)


@require_POST
def api_update(request, item_id):
    if not _has_permission(request, "update_diary_items"):
        return _error("You do not have permission to update diary entries.", status=403)
    try:
        payload = _json_payload(request)
        item = get_object_or_404(
            _scoped_items(request).filter(deleted_at__isnull=True), pk=item_id
        )
        company_id, _branch_id = _user_scope(request)
        updated = update_diary_item(item, payload, company_id=company_id)
        return JsonResponse({"success": True, "message": "Diary entry updated.", "id": updated.pk})
    except DiaryServiceError as exc:
        return _error(exc)
    except Http404:
        raise
    except Exception:
        return _error("Unable to update this diary entry.", status=500)


@require_POST
def api_action(request, item_id):
    if not _has_permission(request, "update_diary_items"):
        return _error("You do not have permission to update diary entries.", status=403)
    try:
        payload = _json_payload(request)
        item = get_object_or_404(
            _scoped_items(request).filter(deleted_at__isnull=True), pk=item_id
        )
        result = apply_diary_action(item, payload)
        return JsonResponse({"success": True, "message": "Action saved.", "id": result.pk})
    except DiaryServiceError as exc:
        return _error(exc)
    except Http404:
        raise
    except Exception:
        return _error("Unable to save this action.", status=500)


@require_POST
def api_delete(request, item_id):
    if not _has_permission(request, "delete_diary_items"):
        return _error("You do not have permission to delete diary entries.", status=403)
    try:
        payload = _json_payload(request)
        item = get_object_or_404(
            _scoped_items(request).filter(deleted_at__isnull=True), pk=item_id
        )
        soft_delete_diary_item(item, note=payload.get("note", ""))
        return JsonResponse({"success": True, "message": "Diary entry deleted."})
    except DiaryServiceError as exc:
        return _error(exc)
    except Http404:
        raise
    except Exception:
        return _error("Unable to delete this diary entry.", status=500)
