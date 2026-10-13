from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from apps.quotation.models import Quotation
from apps.sale.models import Features , Invoice

ZERO = Decimal("0.00")

from django.db.models import Count


def get_quotation_book_data(date_from, date_to, search_query=""):

    columns = [
        {"key": "date", "label": "Date", "width": "9%"},
        # {"key": "time", "label": "Time", "width": "7%"},
        {"key": "v_type", "label": "Vch Type", "width": "7%"},
        {"key": "vno", "label": "Quotation #", "width": "11%"},
        {"key": "acc_code", "label": "A/C Code", "width": "9%"},
        {"key": "desc", "label": "Remarks / Description", "width": "20%"},
        {"key": "total_items", "label": "Items", "width": "6%"},
        {"key": "net_total", "label": "Net Total", "width": "10%"},
        {"key": "converted", "label": "Status", "width": "10%"},
        {"key": "user", "label": "User", "width": "7%"},
    ]

    qs = Quotation.objects.filter(
        date__range=[date_from, date_to],
        is_header=True,
    ).order_by("-dateent", "-bill_no")

    if search_query:
        qs = qs.filter(bill_no__icontains=search_query)

    quotations = list(qs)
    all_qo_nos = [q.bill_no for q in quotations if q.bill_no]

    # ── ONE QUERY: count per quotation ──
    # Returns: {'QO-1001': 2, 'QO-1002': 1 ...}
    converted_counts = dict(
        Invoice.objects.filter(
            header_quo_con_no__in=all_qo_nos,
            is_header=True
        ).values('header_quo_con_no').annotate(cnt=Count('id')).values_list('header_quo_con_no', 'cnt')
    )

    data = []
    for row in quotations:
        d_val = row.date.strftime("%d-%b-%Y") if row.date else (row.dateent.strftime("%d-%b-%Y") if row.dateent else "")
        t_val = row.dateent.strftime("%H:%M") if row.dateent else ""
        net_tot = row.header_net_total or ZERO

        cnt = converted_counts.get(row.bill_no, 0)  # <-- per quotation count

        data.append({
            "date": d_val,
            "time": t_val,
            "v_type": "QOT",
            "vno": row.bill_no,
            "acc_code": row.header_acc_code or "",
            "desc": row.header_remarks or "Quotation",
            "total_items": row.header_total_items or 0,
            "net_total": f"{net_tot:,.2f}",
            "converted": "Converted" if cnt > 0 else "Pending",
            "converted_count": cnt,  # 0,1,2,3...
            "is_converted": cnt > 0,
            "user": row.user or "",
        })

    return data, columns

# def get_quotation_book_data(date_from, date_to, search_query=""):
#     columns = [
#         {"key": "date", "label": "Date", "width": "11%"},
#         {"key": "time", "label": "Time", "width": "8%"},
#         {"key": "v_type", "label": "Vch Type", "width": "9%"},
#         {"key": "vno", "label": "Quotation #", "width": "11%"},
#         {"key": "acc_code", "label": "A/C Code", "width": "10%"},
#         {"key": "desc", "label": "Remarks / Description", "width": "23%"},
#         {"key": "total_items", "label": "Items", "width": "8%"},
#         {"key": "net_total", "label": "Net Total", "width": "12%"},
#         {"key": "user", "label": "User", "width": "8%"},
#     ]



#     qs = Quotation.objects.filter(
#         date__range=[date_from, date_to],
#         is_header=True,
#     ).order_by("-dateent", "-bill_no")

#     if search_query:
#         qs = qs.filter(bill_no__icontains=search_query)

#     data = []
#     for row in qs:
#         d_val = row.date.strftime("%d-%b-%Y") if row.date else (row.dateent.strftime("%d-%b-%Y") if row.dateent else "")
#         t_val = row.dateent.strftime("%H:%M") if row.dateent else ""
#         net_tot = row.header_net_total or ZERO

#         data.append(
#             {
#                 "date": d_val,
#                 "time": t_val,
#                 "v_type": "QOT",
#                 "vno": row.bill_no,
#                 "acc_code": row.header_acc_code or "",
#                 "desc": row.header_remarks or "Quotation",
#                 "total_items": row.header_total_items or 0,
#                 "net_total": f"{net_tot:,.2f}",
#                 "user": row.user or "",
#             }
#         )

#     return data, columns


@csrf_exempt
def quotation_book(request):
    can_view, message = get_user_perms(request, 'view_own_quotation')
    if not can_view:
        return redirect('page_not_found')
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
    search_query = ""

    if request.method == "POST":
        date_from = request.POST.get("date_from") or date.today().isoformat()
        date_to = request.POST.get("date_to") or date.today().isoformat()
        search_query = request.POST.get("search_query") or ""

    data, columns = get_quotation_book_data(date_from, date_to, search_query)

    context = {
        "data": data,
        "columns": columns,
        "date_from": date_from,
        "date_to": date_to,
        "search_query": search_query,
        "features": features,
    }
    return render(request, "reports/quotation_book.html", context)
