from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, F, Case, When, DecimalField
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt

from apps.sale.models import Invoice, Features
from apps.purchase.models import Purchase

ZERO = Decimal("0.00")



def get_item_wise_profit_data(request,date_from, date_to, profit_filter="all"):
    can_view, message = get_user_perms(request, 'see_reports')
    if not can_view:
        return redirect('page_not_found')

    columns = [
        {"key": "item_name", "label": "Item Name", "width": "22%"},
        {"key": "profit", "label": "Profit", "width": "10%"},
        {"key": "sold_qty", "label": "Sold Qty", "width": "8%"},
        {"key": "avg_sale_rate", "label": "Avg Sale Rate", "width": "10%"},
        {"key": "total_net_sale", "label": "Total Net Sale", "width": "11%"},
        {"key": "avg_cost", "label": "Avg Cost", "width": "10%"},
        {"key": "total_net_cost", "label": "Total Cost", "width": "11%"},
        {"key": "purchase_qty", "label": "Total Pur Qty", "width": "8%"},
        # {"key": "total_net_purchase", "label": "Total Cost", "width": "10%"},
    ]

    # 1. Fetch Sales Aggregation grouped by inv_id, prod_name (O(N) DB aggregation)
    sales_qs = (
        Invoice.objects.filter(
            date__range=[date_from, date_to],
        )
        .values("inv_id", "prod_name")
        .annotate(
            total_sold_qty=Coalesce(Sum(F("qty")*F('pack_qty')), ZERO),
            total_net_sale=Coalesce(Sum("row_net_total"), ZERO),
            total_net_cost=Coalesce(
                Sum(
                    Case(
                        When(row_net_cost__gt=0, then=F("row_net_cost")),
                        default=(F("qty")*F("pack_qty")) * F("row_rate_cost"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                ZERO,
            ),
        )
    )

    # 2. Fetch Purchases Aggregation grouped by inv_id, prod_name (O(N) DB aggregation)
    purchases_qs = (
        Purchase.objects.filter(
            date__range=[date_from, date_to],
        )
        .values("inv_id", "prod_name")
        .annotate(
            total_purchase_qty=Coalesce(Sum(F("qty")*F("pack_qty")), ZERO),
            total_net_purchase=Coalesce(Sum("row_net_total"), ZERO),
        )
    )

    # 3. Merge in O(N) using dictionary mapping
    items_map = {}

    for row in sales_qs:
        key = row["inv_id"] if row["inv_id"] else row["prod_name"]
        if not key:
            continue
        items_map[key] = {
            "inv_id": row["inv_id"],
            "item_name": row["prod_name"] or f"Item {row['inv_id']}",
            "sold_qty": Decimal(str(row["total_sold_qty"] or 0)),
            "total_net_sale": Decimal(str(row["total_net_sale"] or 0)),
            "total_net_cost": Decimal(str(row["total_net_cost"] or 0)),
            "purchase_qty": ZERO,
            "total_net_purchase": ZERO,
        }

    for row in purchases_qs:
        key = row["inv_id"] if row["inv_id"] else row["prod_name"]
        if not key:
            continue
        p_qty = Decimal(str(row["total_purchase_qty"] or 0))
        p_net = Decimal(str(row["total_net_purchase"] or 0))

        if key in items_map:
            items_map[key]["purchase_qty"] = p_qty
            items_map[key]["total_net_purchase"] = p_net
        else:
            items_map[key] = {
                "inv_id": row["inv_id"],
                "item_name": row["prod_name"] or f"Item {row['inv_id']}",
                "sold_qty": ZERO,
                "total_net_sale": ZERO,
                "total_net_cost": ZERO,
                "purchase_qty": p_qty,
                "total_net_purchase": p_net,
            }

    data = []
    tot_sold_qty = ZERO
    tot_net_sale = ZERO
    tot_net_cost = ZERO
    tot_profit = ZERO
    tot_purchase_qty = ZERO
    tot_net_purchase = ZERO

    # 4. Calculate metrics and apply filter
    for item in items_map.values():
        sold_qty = item["sold_qty"]
        net_sale = item["total_net_sale"]
        net_cost = item["total_net_cost"]
        purchase_qty = item["purchase_qty"]
        net_purchase = item["total_net_purchase"]

        avg_sale_rate = (net_sale / sold_qty) if sold_qty > ZERO else ZERO
        if sold_qty > ZERO:
            avg_cost = (net_cost / sold_qty)
        elif purchase_qty > ZERO:
            avg_cost = (net_purchase / purchase_qty)
        else:
            avg_cost = ZERO

        profit = net_sale - net_cost

        # Filter:
        # 'sale_gt_cost': Sale rate > Cost (avg_sale_rate > avg_cost)
        # 'cost_gt_sale': Cost > Sale rate (avg_cost > avg_sale_rate)
        # 'sale_eq_cost': Sale rate == Cost (avg_sale_rate == avg_cost)
        if profit_filter == "sale_gt_cost":
            if not (avg_sale_rate > avg_cost):
                continue
        elif profit_filter == "cost_gt_sale":
            if not (avg_cost > avg_sale_rate):
                continue
        elif profit_filter == "sale_eq_cost":
            if not (avg_sale_rate == avg_cost):
                continue

        tot_sold_qty += sold_qty
        tot_net_sale += net_sale
        tot_net_cost += net_cost
        tot_profit += profit
        tot_purchase_qty += purchase_qty
        tot_net_purchase += net_purchase

        data.append(
            {
                "item_name": item["item_name"],
                "sold_qty": f"{sold_qty:,.2f}" if sold_qty % 1 != 0 else f"{int(sold_qty)}",
                "avg_sale_rate": f"{avg_sale_rate:,.2f}",
                "total_net_sale": f"{net_sale:,.2f}",
                "avg_cost": f"{avg_cost:,.2f}",
                "total_net_cost": f"{net_cost:,.2f}",
                "profit": f"{profit:,.2f}",
                "purchase_qty": f"{purchase_qty:,.2f}" if purchase_qty % 1 != 0 else f"{int(purchase_qty)}",
                "total_net_purchase": f"{purchase_qty*avg_cost:,.2f}",
            }
        )

    data.sort(key=lambda x: x["item_name"])

    summary = {
        "total_sold_qty": f"{tot_sold_qty:,.2f}" if tot_sold_qty % 1 != 0 else f"{int(tot_sold_qty)}",
        "total_net_sale": f"{tot_net_sale:,.2f}",
        "total_net_cost": f"{tot_net_cost:,.2f}",
        "total_profit": f"{tot_profit:,.2f}",
        "total_purchase_qty": f"{tot_purchase_qty:,.2f}" if tot_purchase_qty % 1 != 0 else f"{int(tot_purchase_qty)}",
        # "total_net_purchase": f"{tot_net_purchase:,.2f}",
        "total_net_purchase": f"{tot_purchase_qty*tot_net_cost:,.2f}",
    }

    return data, columns, summary


@csrf_exempt
def item_wise_profit_and_loss(request):
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

    data, columns, summary = get_item_wise_profit_data(request,date_from, date_to, profit_filter)

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
    return render(request, "reports/item_wise_profit_and_loss.html", context)
