from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, F, Case, When, DecimalField, Min
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt

from apps.sale.models import Invoice, Features

ZERO = Decimal("0.00")



def get_bill_wise_profit_data(request,date_from, date_to, profit_filter="all"):
    can_view, message = get_user_perms(request, 'see_reports')
    if not can_view:
        return redirect('page_not_found')

    columns = [
        {"key": "bill_no", "label": "Bill #", "width": "12%"},
        {"key": "date", "label": "Date", "width": "14%"},
        {"key": "total_sold_qty", "label": "Sold Qty", "width": "14%"},
        {"key": "total_net_sale", "label": "Sale Amount", "width": "16%"},
        {"key": "total_net_cost", "label": "Total Cost (COGS)", "width": "16%"},
        {"key": "profit", "label": "Profit / (Loss)", "width": "14%"},
        {"key": "profit_margin", "label": "Margin %", "width": "14%"},
    ]

    # Group by bill_no in date range (O(N) aggregation)
    bills_qs = (
        Invoice.objects.filter(
            date__range=[date_from, date_to],
        )
        .values("bill_no")
        .annotate(
            bill_date=Min("date"),
            total_sold_qty=Coalesce(Sum(F("pack_qty")*F("qty") if F("pack_qty") else F("qty")), ZERO),
            total_net_sale=Coalesce(Sum("row_net_total"), ZERO),
            total_net_cost=Coalesce(
                Sum(
                    Case(
                        When(row_net_cost__gt=0, then=F("row_net_cost")),
                        default=F("row_net_cost"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                ZERO,
            ),
        )
        .order_by("-bill_no")
    )

    data = []
    tot_bills = 0
    tot_sold_qty = ZERO
    tot_net_sale = ZERO
    tot_net_cost = ZERO
    tot_profit = ZERO

    for row in bills_qs:
        bill_no = row["bill_no"]
        if bill_no is None:
            continue

        sold_qty = Decimal(str(row["total_sold_qty"] or 0))
        net_sale = Decimal(str(row["total_net_sale"] or 0))
        net_cost = Decimal(str(row["total_net_cost"] or 0))
        profit = net_sale - net_cost

        margin_pct = (profit / net_sale * 100) if net_sale != ZERO else ZERO

        # Filter check:
        # 'sale_gt_cost': Sale > Cost (profit > 0)
        # 'cost_gt_sale': Cost > Sale (profit < 0)
        # 'sale_eq_cost': Sale == Cost (profit == 0)
        if profit_filter == "sale_gt_cost":
            if not (net_sale > net_cost):
                continue
        elif profit_filter == "cost_gt_sale":
            if not (net_cost > net_sale):
                continue
        elif profit_filter == "sale_eq_cost":
            if not (net_sale == net_cost):
                continue

        tot_bills += 1
        tot_sold_qty += sold_qty
        tot_net_sale += net_sale
        tot_net_cost += net_cost
        tot_profit += profit

        data.append(
            {
                "bill_no": f"INV-{bill_no}" if not str(bill_no).startswith("INV-") else str(bill_no),
                "raw_bill_no": bill_no,
                "date": str(row["bill_date"] or ""),
                "total_sold_qty": f"{sold_qty:,.2f}" if sold_qty % 1 != 0 else f"{int(sold_qty)}",
                "total_net_sale": f"{net_sale:,.2f}",
                "total_net_cost": f"{net_cost:,.2f}",
                "profit": f"{profit:,.2f}",
                "profit_margin": f"{margin_pct:.1f}%",
            }
        )

    overall_margin = (tot_profit / tot_net_sale * 100) if tot_net_sale != ZERO else ZERO

    summary = {
        "total_bills": tot_bills,
        "total_sold_qty": f"{tot_sold_qty:,.2f}" if tot_sold_qty % 1 != 0 else f"{int(tot_sold_qty)}",
        "total_net_sale": f"{tot_net_sale:,.2f}",
        "total_net_cost": f"{tot_net_cost:,.2f}",
        "total_profit": f"{tot_profit:,.2f}",
        "overall_margin": f"{overall_margin:.1f}%",
    }

    return data, columns, summary


@csrf_exempt
def bill_wise_profit_and_loss(request):
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

    date_from = date.today().isoformat()
    date_to = date.today().isoformat()
    profit_filter = "all"

    if request.method == "POST":
        date_from = request.POST.get("date_from") or date.today().isoformat()
        date_to = request.POST.get("date_to") or date.today().isoformat()
        profit_filter = request.POST.get("profit_filter") or request.POST.get("v_type") or "all"

    data, columns, summary = get_bill_wise_profit_data(request,date_from, date_to, profit_filter)

    context = {
        "data": data,
        "columns": columns,
        "summary": summary,
        "date_from": date_from,
        "date_to": date_to,
        "profit_filter": profit_filter,
        "v_type": profit_filter,
        "features": features,
    }
    return render(request, "reports/bill_wise_profit_and_loss.html", context)
