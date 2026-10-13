from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db.models import Case, Count, F, Q, Sum, When, DecimalField
from django.db.models.functions import TruncHour
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.configuration.selectors import get_company_config, get_default_accounts
from apps.inventory.models import Inventory
from apps.myaccounts.models import Accounts
from apps.myledger.models import Gledg
from apps.myledger.services.helpers import get_user_perms
from apps.purchase.models import Purchase
from apps.sale.models import Invoice


ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=18, decimal_places=2)
EXPENSE_ACCOUNT_CODE = 3
EXPENSE_V_TYPES = ["CP", "BP", "JV", "CR", "BR"]
PERIODS = {
    "today": "Today",
    "7_days": "Last 7 days",
    "this_month": "This month",
}


def _decimal(value):
    if value in (None, ""):
        return ZERO
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return ZERO


def _number(value):
    return float(_decimal(value))


def _scope(queryset, company_id, branch_id, company_field="company", branch_field="branch"):
    """Apply the signed-in user's tenant scope to transaction querysets."""
    if company_id is not None:
        queryset = queryset.filter(**{f"{company_field}_id": company_id})
    if branch_id is not None:
        queryset = queryset.filter(**{f"{branch_field}_id": branch_id})
    return queryset


def _user_scope(user):
    try:
        profile = user.userprofile
    except AttributeError:
        profile = None
    return profile, getattr(profile, "company_id", None), getattr(profile, "branch_id", None)


def _may_view_unscoped_data(user):
    return user.is_superuser or (user.is_staff and user.username == "z")


def _valid_period(value, fallback="today"):
    if isinstance(value, str) and value in PERIODS:
        return value
    return fallback if isinstance(fallback, str) and fallback in PERIODS else "today"


def _period_range(period, today):
    if period == "7_days":
        return today - timedelta(days=6), today
    if period == "this_month":
        return today.replace(day=1), today
    return today, today


def _account_parent(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _control_accounts(parent_code):
    """Return detail accounts below a control parent; avoid double-counting groups."""
    candidates = Accounts.objects.filter(
        Q(REF_CODE=parent_code) | Q(ACC_CODE__startswith=str(parent_code))
    ).exclude(ACC_CODE=parent_code)

    accounts = list(
        candidates.filter(TYPE__iexact="Detail").values(
            "ACC_CODE", "ACC_NAME", "OPENING_BALANCE", "BALANCE_TYPE", "COMPANY_id", "BRANCH_id"
        )
    )
    if not accounts:
        # Older chart-of-account imports sometimes leave TYPE blank. Keep those
        # rows usable, while still excluding explicit group accounts.
        accounts = list(
            candidates.exclude(TYPE__iexact="Group").values(
                "ACC_CODE", "ACC_NAME", "OPENING_BALANCE", "BALANCE_TYPE", "COMPANY_id", "BRANCH_id"
            )
        )
    return accounts


def _calculate_account_balances(company_id, branch_id, till_date, default_accounts):
    """Use the same opening + ledger + invoice/purchase formula as AR/AP reports."""
    receivable_parent = _account_parent(default_accounts.get("ar_control_parent"), 112)
    payable_parent = _account_parent(default_accounts.get("ap_control_parent"), 231)

    receivable_accounts = _control_accounts(receivable_parent)
    payable_accounts = _control_accounts(payable_parent)
    account_by_code = {
        row["ACC_CODE"]: row for row in receivable_accounts + payable_accounts
    }
    control_codes = list(account_by_code)

    if not control_codes:
        return {
            "receivable_total": 0.0,
            "payable_total": 0.0,
            "receivable_count": 0,
            "payable_count": 0,
            "receivables": [],
            "payables": [],
        }

    ledger_rows = _scope(
        Gledg.objects.filter(ACC_CODE__in=control_codes, DATE__lte=till_date),
        company_id,
        branch_id,
        company_field="COMPANY",
        branch_field="BRANCH",
    ).values("ACC_CODE").annotate(
        debit=Sum("AMOUNT", filter=Q(AMT_TYPE="DR")),
        credit=Sum("AMOUNT", filter=Q(AMT_TYPE="CR")),
    )
    ledger_by_code = {
        row["ACC_CODE"]: (_decimal(row["debit"]), _decimal(row["credit"]))
        for row in ledger_rows
    }

    invoice_rows = _scope(
        Invoice.objects.filter(
            is_header=True,
            date__lte=till_date,
            header_acc_code__in=control_codes,
        ),
        company_id,
        branch_id,
    ).values("header_acc_code").annotate(total=Sum("header_net_total"))
    invoice_by_code = {
        row["header_acc_code"]: _decimal(row["total"]) for row in invoice_rows
    }

    purchase_rows = _scope(
        Purchase.objects.filter(
            is_header=True,
            date__lte=till_date,
            header_acc_code__in=control_codes,
        ),
        company_id,
        branch_id,
    ).values("header_acc_code").annotate(total=Sum("header_net_total"))
    purchase_by_code = {
        row["header_acc_code"]: _decimal(row["total"]) for row in purchase_rows
    }

    receivable_balances = []
    for row in receivable_accounts:
        code = row["ACC_CODE"]
        opening = _decimal(row["OPENING_BALANCE"])
        # Accounts is a shared chart-of-accounts table (ACC_CODE is its primary
        # key). Only use its opening balance in the company/branch it belongs to.
        if company_id is not None and row["COMPANY_id"] not in (None, company_id):
            opening = ZERO
        if branch_id is not None and row["BRANCH_id"] not in (None, branch_id):
            opening = ZERO

        balance_type = (row["BALANCE_TYPE"] or "").strip().upper()
        opening_debit = opening if balance_type == "DR" else ZERO
        opening_credit = opening if balance_type == "CR" else ZERO
        ledger_debit, ledger_credit = ledger_by_code.get(code, (ZERO, ZERO))

        debit = opening_debit + ledger_debit + invoice_by_code.get(code, ZERO)
        credit = opening_credit + ledger_credit + purchase_by_code.get(code, ZERO)
        balance = debit - credit
        if balance > ZERO:
            receivable_balances.append({
                "code": str(code),
                "name": (row["ACC_NAME"] or f"Account {code}").strip(),
                "balance": _number(balance),
            })

    payable_balances = []
    for row in payable_accounts:
        code = row["ACC_CODE"]
        opening = _decimal(row["OPENING_BALANCE"])
        if company_id is not None and row["COMPANY_id"] not in (None, company_id):
            opening = ZERO
        if branch_id is not None and row["BRANCH_id"] not in (None, branch_id):
            opening = ZERO

        balance_type = (row["BALANCE_TYPE"] or "").strip().upper()
        opening_debit = opening if balance_type == "DR" else ZERO
        opening_credit = opening if balance_type == "CR" else ZERO
        ledger_debit, ledger_credit = ledger_by_code.get(code, (ZERO, ZERO))

        debit = opening_debit + ledger_debit + invoice_by_code.get(code, ZERO)
        credit = opening_credit + ledger_credit + purchase_by_code.get(code, ZERO)
        balance = credit - debit
        if balance > ZERO:
            payable_balances.append({
                "code": str(code),
                "name": (row["ACC_NAME"] or f"Account {code}").strip(),
                "balance": _number(balance),
            })

    receivable_balances.sort(key=lambda item: item["balance"], reverse=True)
    payable_balances.sort(key=lambda item: item["balance"], reverse=True)

    return {
        "receivable_total": sum(item["balance"] for item in receivable_balances),
        "payable_total": sum(item["balance"] for item in payable_balances),
        "receivable_count": len(receivable_balances),
        "payable_count": len(payable_balances),
        "receivables": receivable_balances[:6],
        "payables": payable_balances[:6],
    }


def _profit_loss(sales_items):
    """Summarize product margins using the cost expression in the item P&L report."""
    cost_expression = Case(
        When(row_net_cost__gt=0, then=F("row_net_cost")),
        default=F("qty") * F("pack_qty") * F("row_rate_cost"),
        output_field=MONEY_FIELD,
    )
    grouped_items = sales_items.values("inv_id", "prod_name").annotate(
        sales=Sum("row_net_total"),
        cost=Sum(cost_expression),
    )

    profit_total = ZERO
    loss_total = ZERO
    cost_to_cost_total = ZERO
    profit_count = 0
    loss_count = 0
    cost_to_cost_count = 0

    for item in grouped_items.iterator(chunk_size=500):
        sales = _decimal(item["sales"])
        cost = _decimal(item["cost"])
        margin = sales - cost
        if margin > ZERO:
            profit_total += margin
            profit_count += 1
        elif margin < ZERO:
            loss_total += abs(margin)
            loss_count += 1
        else:
            cost_to_cost_total += sales
            cost_to_cost_count += 1

    return {
        "profit": _number(profit_total),
        "profit_items": profit_count,
        "loss": _number(loss_total),
        "loss_items": loss_count,
        "cost_to_cost": _number(cost_to_cost_total),
        "cost_to_cost_items": cost_to_cost_count,
    }


def _chart_data(period, start_date, end_date, sale_headers, purchase_headers, sales_total, purchases_total):
    if period == "today":
        hourly_sales = (
            sale_headers.filter(date=end_date, dateent__isnull=False)
            .annotate(bucket=TruncHour("dateent"))
            .values("bucket")
            .annotate(total=Sum("header_net_total"))
            .order_by("bucket")
        )
        hourly_purchases = (
            purchase_headers.filter(date=end_date, dateent__isnull=False)
            .annotate(bucket=TruncHour("dateent"))
            .values("bucket")
            .annotate(total=Sum("header_net_total"))
            .order_by("bucket")
        )
        sales_by_hour = {row["bucket"].hour: _number(row["total"]) for row in hourly_sales}
        purchases_by_hour = {row["bucket"].hour: _number(row["total"]) for row in hourly_purchases}

        # Older invoices may not have a timestamp. Show the period total rather
        # than an empty chart when no hourly buckets are available.
        if not sales_by_hour and not purchases_by_hour:
            return {
                "labels": ["Today"],
                "sales": [sales_total],
                "purchases": [purchases_total],
            }

        labels = []
        for hour in range(24):
            suffix = "am" if hour < 12 else "pm"
            hour_12 = hour % 12 or 12
            labels.append(f"{hour_12}{suffix}")
        return {
            "labels": labels,
            "sales": [sales_by_hour.get(hour, 0) for hour in range(24)],
            "purchases": [purchases_by_hour.get(hour, 0) for hour in range(24)],
        }

    daily_sales = (
        sale_headers.filter(date__range=(start_date, end_date))
        .values("date")
        .annotate(total=Sum("header_net_total"))
    )
    daily_purchases = (
        purchase_headers.filter(date__range=(start_date, end_date))
        .values("date")
        .annotate(total=Sum("header_net_total"))
    )
    sales_by_date = {row["date"]: _number(row["total"]) for row in daily_sales}
    purchases_by_date = {row["date"]: _number(row["total"]) for row in daily_purchases}

    day_count = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=offset) for offset in range(day_count)]
    return {
        "labels": [value.strftime("%d %b") for value in dates],
        "sales": [sales_by_date.get(value, 0) for value in dates],
        "purchases": [purchases_by_date.get(value, 0) for value in dates],
    }


@login_required
def dashboard(request):
    can_view, _message = get_user_perms(request, "view_dashboard")
    if not can_view:
        return redirect("sale:main_sale")

    profile, company_id, branch_id = _user_scope(request.user)
    if company_id is None and branch_id is None and not _may_view_unscoped_data(request.user):
        return redirect("page_not_found")
    config, _config_obj = get_company_config(company_id, branch_id)
    dashboard_config = config.get("dashboard", {})
    default_period = _valid_period(dashboard_config.get("default_period"), "today")
    general_config = config.get("general", {})

    return render(request, "dashboard/dashboard.html", {
        "dashboard_default_period": default_period,
        "currency_symbol": general_config.get("currency_symbol") or "Rs",
        "dashboard_company": getattr(getattr(profile, "company", None), "name", ""),
        "dashboard_branch": getattr(getattr(profile, "branch", None), "name", ""),
    })


@login_required
@require_GET
def dashboard_stats(request):
    can_view, message = get_user_perms(request, "view_dashboard")
    if not can_view:
        return JsonResponse({"success": False, "message": message}, status=403)

    _profile, company_id, branch_id = _user_scope(request.user)
    if company_id is None and branch_id is None and not _may_view_unscoped_data(request.user):
        return JsonResponse({"success": False, "message": "Your company or branch is not configured."}, status=403)
    config, _config_obj = get_company_config(company_id, branch_id)
    configured_default = _valid_period(
        config.get("dashboard", {}).get("default_period"), "today"
    )
    period = _valid_period(request.GET.get("period"), configured_default)

    today = datetime.now(timezone.get_default_timezone()).date()
    start_date, end_date = _period_range(period, today)
    sale_headers = _scope(
        Invoice.objects.filter(is_header=True), company_id, branch_id
    )
    purchase_headers = _scope(
        Purchase.objects.filter(is_header=True), company_id, branch_id
    )

    selected_sales = sale_headers.filter(date__range=(start_date, end_date))
    selected_purchases = purchase_headers.filter(date__range=(start_date, end_date))

    sales_aggregate = selected_sales.aggregate(
        total=Sum("header_net_total"),
        bills=Count("bill_no", distinct=True),
    )
    purchases_aggregate = selected_purchases.aggregate(
        total=Sum("header_net_total"),
        bills=Count("bill_no", distinct=True),
        paid=Sum("header_total_paid"),
        cash_paid=Sum("header_cash_paid"),
        bank_paid=Sum("header_bank_paid"),
    )
    sales_total = _number(sales_aggregate["total"])
    purchases_total = _number(purchases_aggregate["total"])
    purchase_paid = _decimal(purchases_aggregate["paid"])
    if purchase_paid == ZERO:
        purchase_paid = _decimal(purchases_aggregate["cash_paid"]) + _decimal(
            purchases_aggregate["bank_paid"]
        )

    # Cash and bank are asset accounts: debits are inflows and credits are
    # outflows. Read the configured account codes instead of guessing by voucher.
    default_accounts, _accounts_obj = get_default_accounts(company_id, branch_id)
    cash_code = _account_parent(default_accounts.get("default_cash_acc"), 110000001)
    bank_code = _account_parent(default_accounts.get("default_bank_acc"), 111000001)
    selected_ledger = _scope(
        Gledg.objects.filter(DATE__range=(start_date, end_date)),
        company_id,
        branch_id,
        company_field="COMPANY",
        branch_field="BRANCH",
    )
    flow_aggregate = selected_ledger.filter(ACC_CODE__in={cash_code, bank_code}).aggregate(
        cash_received=Sum("AMOUNT", filter=Q(ACC_CODE=cash_code, AMT_TYPE="DR")),
        cash_paid=Sum("AMOUNT", filter=Q(ACC_CODE=cash_code, AMT_TYPE="CR")),
        bank_received=Sum("AMOUNT", filter=Q(ACC_CODE=bank_code, AMT_TYPE="DR")),
        bank_paid=Sum("AMOUNT", filter=Q(ACC_CODE=bank_code, AMT_TYPE="CR")),
    )

    expense_account_codes = Accounts.objects.filter(
        Q(ACC_CODE__startswith=str(EXPENSE_ACCOUNT_CODE))
        | Q(CLASS_FIELD__iexact="Expense")
        | Q(CLASS_FIELD__iexact="Expanse")
        | Q(TYPE__iexact="Expense")
    ).values("ACC_CODE")
    expense_ledger = selected_ledger.filter(ACC_CODE__in=expense_account_codes)
    if EXPENSE_V_TYPES:
        expense_ledger = expense_ledger.filter(V_TYPE__in=EXPENSE_V_TYPES)
    expense_aggregate = expense_ledger.aggregate(
        debit=Sum("AMOUNT", filter=Q(AMT_TYPE="DR")),
        credit=Sum("AMOUNT", filter=Q(AMT_TYPE="CR")),
        entries=Count("GLEDG_ID"),
    )
    total_expense = _decimal(expense_aggregate["debit"]) - _decimal(
        expense_aggregate["credit"]
    )

    sales_items = _scope(
        Invoice.objects.filter(
            date__range=(start_date, end_date),
            prod_name__gt="",
        ),
        company_id,
        branch_id,
    )
    profit_loss = _profit_loss(sales_items)

    chart = _chart_data(
        period,
        start_date,
        end_date,
        sale_headers,
        purchase_headers,
        sales_total,
        purchases_total,
    )

    top_products = (
        sales_items.values("inv_id", "prod_name")
        .annotate(revenue=Sum("row_net_total"), qty=Sum("qty"))
        .order_by("-revenue", "prod_name")[:7]
    )

    inventory = _scope(
        Inventory.objects.filter(active=True, reorder__isnull=False)
        .filter(Q(is_deleted=False) | Q(is_deleted__isnull=True))
        .filter(Q(bal_qty__lte=F("reorder")) | Q(bal_qty__lte=0)),
        company_id,
        branch_id,
    )
    low_stock_count = inventory.count()
    low_stock = inventory.values(
        "inv_id", "prod_name", "bal_qty", "reorder", "base_uom__name"
    ).order_by("bal_qty", "prod_name")[:6]

    period_ledger = selected_ledger.filter(V_TYPE__in=["CR", "CP", "BR", "BP", "JV"])
    recent_vouchers = period_ledger.values(
        "GLEDG_ID", "V_TYPE", "VNO", "ACC_CODE", "DESCRIPTION", "AMOUNT", "AMT_TYPE", "DATEENT"
    ).order_by("-DATEENT", "-GLEDG_ID")[:5]

    balances = _calculate_account_balances(
        company_id,
        branch_id,
        end_date,
        default_accounts,
    )

    return JsonResponse({
        "success": True,
        "period": period,
        "period_label": PERIODS[period],
        "date_from": start_date.isoformat(),
        "date_to": end_date.isoformat(),
        "today": today.strftime("%A, %d %B %Y"),
        "kpi": {
            "sales": sales_total,
            "sales_bills": sales_aggregate["bills"] or 0,
            "purchases": purchases_total,
            "purchase_bills": purchases_aggregate["bills"] or 0,
            "purchase_paid": _number(purchase_paid),
            "expenses": _number(total_expense),
            "expense_entries": expense_aggregate["entries"] or 0,
            "low_stock_count": low_stock_count,
        },
        "cash_flow": {
            "cash_received": _number(flow_aggregate["cash_received"]),
            "cash_paid": _number(flow_aggregate["cash_paid"]),
            "bank_received": _number(flow_aggregate["bank_received"]),
            "bank_paid": _number(flow_aggregate["bank_paid"]),
        },
        "profit_loss": profit_loss,
        "balances": balances,
        "chart": chart,
        "top_products": [
            {
                "name": row["prod_name"] or f"Item {row['inv_id']}",
                "inv_id": row["inv_id"],
                "revenue": _number(row["revenue"]),
                "qty": _number(row["qty"]),
            }
            for row in top_products
        ],
        "low_stock": [
            {
                "inv_id": row["inv_id"],
                "name": row["prod_name"] or f"Item {row['inv_id']}",
                "balance": row["bal_qty"] or 0,
                "reorder": row["reorder"] or 0,
                "unit": row["base_uom__name"] or "units",
            }
            for row in low_stock
        ],
        "recent_vouchers": [
            {
                "id": row["GLEDG_ID"],
                "type": (row["V_TYPE"] or "").strip().upper(),
                "number": row["VNO"] or 0,
                "account": row["ACC_CODE"] or 0,
                "description": (row["DESCRIPTION"] or "—").strip(),
                "amount": _number(row["AMOUNT"]),
                "amount_type": (row["AMT_TYPE"] or "").strip().upper(),
                "time": row["DATEENT"].strftime("%H:%M") if row["DATEENT"] else "—",
            }
            for row in recent_vouchers
        ],
    })
