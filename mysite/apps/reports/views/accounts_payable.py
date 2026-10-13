from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, Q
from django.views.decorators.csrf import csrf_exempt

from apps.myaccounts.models import Accounts
from apps.myledger.models import Gledg
from apps.sale.models import Invoice, Features
from apps.purchase.models import Purchase

# ==============================================================================
# GLOBAL CONFIGURATION VARIABLES FOR ACCOUNTS PAYABLE
# ==============================================================================
PAYABLE_PARENT_CODE = 231
PAYABLE_LEVEL = 3

ZERO = Decimal("0.00")



def get_accounts_payable_data(
    request,

    till_date,
    city_filter="",
    parent_code=PAYABLE_PARENT_CODE,
    parent_level=PAYABLE_LEVEL,
):
    """
    Computes Accounts Payable data up to `till_date` for all child/detail
    accounts under parent_code (default 231).
    """
    # 1. Columns Definition
    columns = [
        {"key": "acc_code", "label": "Account Code", "width": "12%"},
        {"key": "acc_name", "label": "Account Name", "width": "28%"},
        {"key": "city", "label": "City", "width": "14%"},
        {"key": "total_debit", "label": "Total Debit", "width": "15%"},
        {"key": "total_credit", "label": "Total Credit", "width": "15%"},
        {"key": "balance", "label": "Payable Balance", "width": "16%"},
    ]

    can_view, message = get_user_perms(request, 'see_payable_statements')
    if not can_view:
        return redirect('page_not_found')
    # 2. Query all matching accounts
    prefix = str(parent_code)
    accounts_qs = Accounts.objects.filter(
        Q(REF_CODE=parent_code) | Q(ACC_CODE__startswith=prefix)
    ).exclude(ACC_CODE=parent_code)

    if city_filter:
        accounts_qs = accounts_qs.filter(CITY__iexact=city_filter)

    accounts_list = list(accounts_qs.order_by("ACC_NAME", "ACC_CODE"))
    account_codes = [acc.ACC_CODE for acc in accounts_list]

    if not account_codes:
        summary = {
            "total_accounts": 0,
            "total_debit": "0.00",
            "total_credit": "0.00",
            "net_balance": "0.00",
            "total_payable": "0.00",
            "total_advance": "0.00",
        }
        return [], columns, summary, []

    # 3. High-performance aggregations up to till_date
    gledg_dr_map = {
        row["ACC_CODE"]: Decimal(str(row["total"] or 0))
        for row in Gledg.objects.filter(
            ACC_CODE__in=account_codes, DATE__lte=till_date, AMT_TYPE="DR"
        )
        .values("ACC_CODE")
        .annotate(total=Sum("AMOUNT"))
    }

    gledg_cr_map = {
        row["ACC_CODE"]: Decimal(str(row["total"] or 0))
        for row in Gledg.objects.filter(
            ACC_CODE__in=account_codes, DATE__lte=till_date, AMT_TYPE="CR"
        )
        .values("ACC_CODE")
        .annotate(total=Sum("AMOUNT"))
    }

    inv_dr_map = {
        row["header_acc_code"]: Decimal(str(row["total"] or 0))
        for row in Invoice.objects.filter(
            header_acc_code__in=account_codes, date__lte=till_date, is_header=True
        )
        .values("header_acc_code")
        .annotate(total=Sum("header_net_total"))
    }

    pur_cr_map = {
        row["header_acc_code"]: Decimal(str(row["total"] or 0))
        for row in Purchase.objects.filter(
            header_acc_code__in=account_codes, date__lte=till_date, is_header=True
        )
        .values("header_acc_code")
        .annotate(total=Sum("header_net_total"))
    }

    # 4. Build row items
    data = []
    tot_debit = ZERO
    tot_credit = ZERO
    tot_payable = ZERO
    tot_advance = ZERO
    all_cities = set()

    for acc in accounts_list:
        code = acc.ACC_CODE
        city_name = (acc.CITY or "").strip()
        if city_name:
            all_cities.add(city_name)

        op_bal = Decimal(str(acc.OPENING_BALANCE or 0.0))
        bal_type = (acc.BALANCE_TYPE or "").strip().upper()
        if bal_type == "DR":
            op_dr = op_bal
            op_cr = ZERO
        elif bal_type == "CR":
            op_dr = ZERO
            op_cr = op_bal
        else:
            op_dr = ZERO
            op_cr = ZERO

        debit = op_dr + gledg_dr_map.get(code, ZERO) + inv_dr_map.get(code, ZERO)
        credit = op_cr + gledg_cr_map.get(code, ZERO) + pur_cr_map.get(code, ZERO)
        # For Payables: Net Payable = Credit - Debit (positive means we owe vendor)
        balance = credit - debit

        tot_debit += debit
        tot_credit += credit
        if balance >= ZERO:
            tot_payable += balance
        else:
            tot_advance += abs(balance)

        if balance != 0:
            data.append(
                {
                    "acc_code": code,
                    "acc_name": acc.ACC_NAME or f"Account {code}",
                    "city": city_name or "-",
                    "raw_debit": debit,
                    "total_debit": f"{debit:,.2f}",
                    "raw_credit": credit,
                    "total_credit": f"{credit:,.2f}",
                    "raw_balance": balance,
                    "balance": f"{balance:,.2f}",
                    "is_negative": balance < ZERO,
                }
            )

    net_balance = tot_credit - tot_debit

    summary = {
        "total_accounts": len(data),
        "total_debit": f"{tot_debit:,.2f}",
        "total_credit": f"{tot_credit:,.2f}",
        "net_balance": f"{net_balance:,.2f}",
        "total_payable": f"{tot_payable:,.2f}",
        "total_advance": f"{tot_advance:,.2f}",
    }

    distinct_cities = sorted(list(all_cities))
    return data, columns, summary, distinct_cities


@csrf_exempt
def accounts_payable(request):
    user = request.user
    try:
        features = Features.objects.get(user=user)
        if not features:
            features = Features.objects.get_or_create(user="All Features")[0]
    except Exception:
        try:
            features = Features.objects.get(user="All Features")
        except Exception:
            features = None

    till_date = date.today().isoformat()
    city_filter = ""

    if request.method == "POST":
        till_date = request.POST.get("till_date") or date.today().isoformat()
        city_filter = request.POST.get("city_filter") or ""
    elif request.method == "GET":
        till_date = request.GET.get("till_date") or date.today().isoformat()
        city_filter = request.GET.get("city_filter") or ""

    data, columns, summary, distinct_cities = get_accounts_payable_data(
        request,
        till_date=till_date,
        city_filter=city_filter,
    )

    context = {
        "data": data,
        "columns": columns,
        "summary": summary,
        "till_date": till_date,
        "city_filter": city_filter,
        "distinct_cities": distinct_cities,
        "features": features,
    }
    return render(request, "reports/accounts_payable.html", context)
