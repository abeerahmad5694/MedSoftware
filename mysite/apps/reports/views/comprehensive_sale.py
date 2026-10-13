from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.db.models import F, Q
from django.views.decorators.csrf import csrf_exempt

from apps.sale.models import Invoice, Features
from apps.configuration.models import Branch
from apps.inventory.models import ItemCategory, Inventory

ZERO = Decimal("0.00")



def get_comprehensive_sale_data(
    
    request,
    date_from,
    date_to,
    cashier="",
    shop_id="",
    category="",
    filter_mode="",
):
    columns = [
        {"key": "prod_name", "label": "Product", "width": "22%"},
        {"key": "qty", "label": "Qty", "width": "6%"},
        {"key": "bill_no", "label": "Receipt#", "width": "9%"},
        {"key": "rate", "label": "S.Price", "width": "8%"},
        {"key": "disc", "label": "Disc", "width": "8%"},
        {"key": "amount", "label": "Amount", "width": "9%"},
        {"key": "date", "label": "Date", "width": "9%"},
        {"key": "time", "label": "Time", "width": "7%"},
        {"key": "user", "label": "Emp.Name", "width": "9%"},
        {"key": "shop_name", "label": "Shop Name", "width": "13%"},
    ]


    

    qs = (
        Invoice.objects.filter(
            date__range=[date_from, date_to],
        )
        .exclude(prod_name="")
        .select_related("branch", "company")
        .order_by("-date", "-dateent", "-bill_no")
    )

    if cashier:
        qs = qs.filter(user__iexact=cashier)
    if shop_id:
        qs = qs.filter(branch_id=shop_id)
    if category:
        matching_inv_ids = list(
            Inventory.objects.filter(category__name__iexact=category).values_list("inv_id", flat=True)
        )
        qs = qs.filter(Q(category__iexact=category) | Q(inv_id__in=matching_inv_ids))

    if filter_mode == "sale_gt_cost":
        qs = qs.filter(rate__gt=F("row_rate_cost"), qty__gte=0)
    elif filter_mode in ("sale_lt_cost", "sale_lte_cost"):
        qs = qs.filter(rate__lt=F("row_rate_cost"), qty__gte=0)
    elif filter_mode == "sale_eq_cost":
        qs = qs.filter(rate=F("row_rate_cost"), qty__gte=0)
    elif filter_mode == "return":
        qs = qs.filter(qty__lt=0)

    data = []
    unique_bills = set()
    total_sold_qty = ZERO
    total_returned_qty = ZERO
    total_item_disc = ZERO
    total_sale_amt = ZERO
    total_return_amt = ZERO

    for row in qs:
        qty_val = Decimal(str(row.qty or 0))
        rate_val = Decimal(str(row.rate or 0))
        amt_val = Decimal(str(row.row_net_total or 0))
        disc_val = Decimal(str(row.row_discount_amount or 0))

        if row.bill_no:
            unique_bills.add(row.bill_no)

        if qty_val >= 0:
            total_sold_qty += qty_val
            total_sale_amt += amt_val
        else:
            total_returned_qty += qty_val
            total_return_amt += amt_val

        total_item_disc += disc_val

        d_str = (
            row.date.strftime("%d-%b-%y")
            if row.date
            else (row.dateent.strftime("%d-%b-%y") if row.dateent else "")
        )
        t_str = row.dateent.strftime("%H:%M") if row.dateent else ""
        shop_name = (
            row.branch.name
            if row.branch
            else (row.company.name if row.company else "")
        )

        data.append(
            {
                "prod_name": row.prod_name,
                "qty": f"{qty_val:g}" if qty_val % 1 == 0 else f"{qty_val:,.2f}",
                "raw_qty": qty_val,
                "bill_no": row.bill_no,
                "rate": f"{rate_val:,.2f}",
                "amount": f"{amt_val:,.2f}",
                "raw_amount": amt_val,
                "disc": f"{disc_val:,.2f}" if disc_val != ZERO else "0",
                "date": d_str,
                "time": t_str,
                "user": row.user or "",
                "shop_name": shop_name,
            }
        )

    net_amt = total_sale_amt + total_return_amt

    summary = {
        "item_disc": f"{total_item_disc:,.2f}",
        "bills_count": len(unique_bills),
        "total_sold_qty": (
            f"{total_sold_qty:g}"
            if total_sold_qty % 1 == 0
            else f"{total_sold_qty:,.2f}"
        ),
        "total_returned_qty": (
            f"{total_returned_qty:g}"
            if total_returned_qty % 1 == 0
            else f"{total_returned_qty:,.2f}"
        ),
        "total_disc": f"{total_item_disc:,.2f}",
        "total_sale": f"{total_sale_amt:,.2f}",
        "total_return": f"{total_return_amt:,.2f}",
        "net_total": f"{net_amt:,.2f}",
        "total_rows": len(data),
    }

    return data, columns, summary


@csrf_exempt
def comprehensive_sale(request):
    user = request.user
    try:
        features = Features.objects.get(user=user)
        if not features:
            features = Features.objects.get_or_create(user="All Features")[0]


        can_view, message = get_user_perms(request, 'view_comprehensive_sale')
        if not can_view:
            return redirect('page_not_found')
    except Exception:
        try:
            features = Features.objects.get(user="All Features")
        except Exception:
            features = None

    date_from = date.today().isoformat()
    date_to = date.today().isoformat()
    cashier = ""
    shop_id = ""
    category = ""
    filter_mode = ""

    if request.method == "POST":
        date_from = request.POST.get("date_from") or date.today().isoformat()
        date_to = request.POST.get("date_to") or date.today().isoformat()
        cashier = request.POST.get("cashier") or ""
        shop_id = request.POST.get("shop_id") or ""
        category = request.POST.get("category") or ""
        filter_mode = request.POST.get("filter_mode") or ""

    data, columns, summary = get_comprehensive_sale_data(
        request,
        date_from=date_from,
        date_to=date_to,
        cashier=cashier,
        shop_id=shop_id,
        category=category,
        filter_mode=filter_mode,
    )

    # Fetch choices for dropdowns
    branches = list(Branch.objects.all().order_by("name"))
    
    item_cat_names = set(
        ItemCategory.objects.exclude(name__isnull=True).exclude(name="").values_list("name", flat=True)
    )
    inv_cat_names = set(
        Invoice.objects.exclude(category__isnull=True).exclude(category="").values_list("category", flat=True)
    )
    inventory_cat_names = set(
        Inventory.objects.exclude(category__name__isnull=True).values_list("category__name", flat=True)
    )
    categories = sorted(list(item_cat_names | inv_cat_names | inventory_cat_names))

    cashiers = list(
        Invoice.objects.exclude(user__isnull=True).exclude(user="")
        .values_list("user", flat=True)
        .distinct()
    )

    context = {
        "data": data,
        "columns": columns,
        "summary": summary,
        "date_from": date_from,
        "date_to": date_to,
        "cashier": cashier,
        "shop_id": str(shop_id),
        "category": category,
        "filter_mode": filter_mode,
        "branches": branches,
        "categories": categories,
        "cashiers": cashiers,
        "features": features,
    }
    return render(request, "reports/comprehensive_sale.html", context)
