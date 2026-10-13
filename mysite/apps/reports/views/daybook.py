from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import render
from django.db.models import Q, Sum, DecimalField
from django.db.models.functions import Coalesce
from django.http import JsonResponse

from apps.myledger.models import Gledg
from apps.sale.models import Invoice, Features
from apps.purchase.models import Purchase
from apps.myaccounts.models import Accounts
from apps.myaccounts.constants import get_default_account

ZERO = Decimal("0.00")



def make_daybook_row(

    date_value,
    dateent,
    v_type,
    vno,
    acc_code,
    desc,
    debit=ZERO,
    credit=ZERO,
    source="",
    source_id=0,
):
    return {
        "date": date_value,
        "dateent": dateent,
        "v_type": v_type,
        "vno": vno,
        "acc_code": acc_code,
        "desc": desc or "",
        "debit": debit or ZERO,
        "credit": credit or ZERO,
        "source": source,
        "source_id": source_id,
    }


def merge_daybook(invoice_qs, purchase_qs, gledg_qs):

    invoice_iter = iter(invoice_qs)
    purchase_iter = iter(purchase_qs)
    gledg_iter = iter(gledg_qs)

    streams = [
        invoice_iter,
        purchase_iter,
        gledg_iter,
    ]

    current = []

    for stream in streams:
        try:
            current.append(next(stream))
        except StopIteration:
            current.append(None)

    while any(row is not None for row in current):

        best_index = None
        best_key = None

        for index, row in enumerate(current):

            if row is None:
                continue

            key = (
                row["date"] or date.min,
                row["dateent"] or date.min,
                row["source_id"] or 0,
            )

            if best_key is None or key < best_key:
                best_key = key
                best_index = index

        row = current[best_index]

        yield row

        try:
            current[best_index] = next(
                streams[best_index]
            )
        except StopIteration:
            current[best_index] = None



def data_colomun(invoice_qs, purchase_qs, gledg_qs):

    columns = [
        {"key": "date", "label": "DATE"},
        {"key": "v_type", "label": "Vch Type"},
        {"key": "vno", "label": "INV/VCH#"},
        {"key": "acc_code", "label": "A/C"},
        {"key": "desc", "label": "Desc"},
        {"key": "debit", "label": "Debit"},
        {"key": "credit", "label": "Credit"},
    ]

    data = []
    summary = {
        "opening_cash": ZERO,
        "opening_bank": ZERO,
        "closing_cash": ZERO,
        "closing_bank": ZERO,
        "total_sales": ZERO,
        "total_purchase": ZERO,
        "cash_received": ZERO,
        "cash_paid": ZERO,
        "bank_received": ZERO,
        "bank_paid": ZERO,
        "total_returns": ZERO,
        "total_discounts": ZERO,
        "net_sales": ZERO,
        "total_collection": ZERO,
        "qty_sold": ZERO,
        "total_item_discount": ZERO,
        "total_invoice_discount": ZERO,
        "total_debit": ZERO,
        "total_credit": ZERO,
        "total_purchase_return": ZERO,
        "total_sales_return": ZERO,
    }

    def add_to_summary(v_type, debit, credit, source):
        debit = debit or ZERO
        credit = credit or ZERO
        summary["total_debit"] += debit
        summary["total_credit"] += credit

        if source == "invoice":
            summary["total_sales"] += debit if debit > 0 else 0
            summary["total_sales_return"] += abs(debit) if debit < 0 else 0 

        elif source == "purchase":
            summary["total_purchase"] += credit if credit > 0 else 0
            summary["total_purchase_return"] += abs(credit) if credit < 0 else 0

        voucher_amount = debit + credit
        if v_type == "CR" and credit > 0:
            summary["cash_received"] += voucher_amount
        elif v_type == "CP" and credit > 0:
            summary["cash_paid"] += voucher_amount
        elif v_type == "BR" and credit > 0:
            summary["bank_received"] += voucher_amount
        elif v_type == "BP" and credit > 0:
            summary["bank_paid"] += voucher_amount

    # INVOICES
    for row in invoice_qs:
        d = row.header_net_total or ZERO
        add_to_summary("INV", d, ZERO, "invoice")
        data.append(
            make_daybook_row(
                date_value=row.date,
                dateent=row.dateent,
                v_type="INV",
                vno=row.bill_no,
                acc_code=row.header_acc_code,
                desc=row.header_remarks or "Sales Invoice",
                debit=d,
                credit=ZERO,
                source="invoice",
                source_id=row.id,
            )
        )

    # PURCHASES
    for row in purchase_qs:
        c = row.header_net_total or ZERO
        add_to_summary("PUR", ZERO, c, "purchase")
        data.append(
            make_daybook_row(
                date_value=row.date,
                dateent=row.dateent,
                v_type="PUR",
                vno=row.bill_no,
                acc_code=row.header_acc_code,
                desc=row.header_remarks or "Purchase",
                debit=ZERO,
                credit=c,
                source="purchase",
                source_id=row.id,
            )
        )

    # GLEDG - hide if SHOW_IN_SALE_RPT = N but still add to summary
    for row in gledg_qs:
        amount = row.AMOUNT or ZERO
        debit = ZERO
        credit = ZERO
        if row.AMT_TYPE == "DR":
            debit = amount
        elif row.AMT_TYPE == "CR":
            credit = amount
        
        # always affect summary
        add_to_summary(row.V_TYPE, debit, credit, "gledg")

        # hide from UI
        show_flag = getattr(row, 'SHOW_IN_SALE_RPT', 'Y')
        if show_flag and str(show_flag).strip().upper() == 'N':
            continue

        data.append(
            make_daybook_row(
                date_value=row.DATE,
                dateent=row.DATEENT,
                v_type=row.V_TYPE,
                vno=row.VNO,
                acc_code=row.ACC_CODE,
                desc=row.DESCRIPTION,
                debit=debit,
                credit=credit,
                source="gledg",
                source_id=row.GLEDG_ID,
            )
        )

    source_priority = {"invoice": 1, "purchase": 2, "gledg": 3}
    data.sort(
        key=lambda x: (
            source_priority.get(x["source"], 99),
            x["dateent"] or date.min,
            x["date"] or date.min,
            x["source_id"] or 0,
        )
    )   

    summary["net_sales"] = summary["total_sales"] - summary["total_returns"] - summary["total_discounts"]
    summary["total_collection"] = summary["cash_received"] + summary["bank_received"]
    summary["closing_cash"] = summary["opening_cash"] + summary["cash_received"] - summary["cash_paid"]
    summary["closing_bank"] = summary["opening_bank"] + summary["bank_received"] - summary["bank_paid"]

    return data, columns, summary


    
# def data_colomun(invoice_qs, purchase_qs, gledg_qs):

#     columns = [
#         {"key": "date", "label": "DATE"},
#         {"key": "v_type", "label": "Vch Type"},
#         {"key": "vno", "label": "INV/VCH#"},
#         {"key": "acc_code", "label": "A/C"},
#         {"key": "desc", "label": "Desc"},
#         {"key": "debit", "label": "Debit"},
#         {"key": "credit", "label": "Credit"},
#         # {"key": "action_btns", "label": "Actions"},
#     ]

#     data = []

#     # =========================================================
#     # INVOICES
#     # =========================================================

#     for row in invoice_qs:

#         data.append(
#             make_daybook_row(
#                 date_value=row.date,
#                 dateent=row.dateent,
#                 v_type="INV",
#                 vno=row.bill_no,
#                 acc_code=row.header_acc_code,
#                 desc=row.header_remarks or "Sales Invoice",
#                 debit=row.header_net_total,
#                 credit=ZERO,
#                 source="invoice",
#                 source_id=row.id,
#             )
#         )

#     # =========================================================
#     # PURCHASES
#     # =========================================================

#     for row in purchase_qs:

#         data.append(
#             make_daybook_row(
#                 date_value=row.date,
#                 dateent=row.dateent,
#                 v_type="PUR",
#                 vno=row.bill_no,
#                 acc_code=row.header_acc_code,
#                 desc=row.header_remarks or "Purchase",
#                 debit=ZERO,
#                 credit=row.header_net_total,
#                 source="purchase",
#                 source_id=row.id,
#             )
#         )

#     # =========================================================
#     # GLEDG
#     # =========================================================

#     for row in gledg_qs:

#         amount = row.AMOUNT or ZERO

#         debit = ZERO
#         credit = ZERO

#         if row.AMT_TYPE == "DR":
#             debit = amount

#         elif row.AMT_TYPE == "CR":
#             credit = amount
        
#         data.append(
#             make_daybook_row(
#                 date_value=row.DATE,
#                 dateent=row.DATEENT,
#                 v_type=row.V_TYPE,
#                 vno=row.VNO,
#                 acc_code=row.ACC_CODE,
#                 desc=row.DESCRIPTION,
#                 debit=debit,
#                 credit=credit,
#                 source="gledg",
#                 source_id=row.GLEDG_ID,
#             )
#         )

#     # =========================================================
#     # SORT
#     #
#     # This keeps original creation order.
#     # Editing dateedit does NOT change sequence.
#     # =========================================================
#     source_priority = {
#     "invoice": 1,
#     "purchase": 2,
#     "gledg": 3,
#      }
        
#     data.sort(
#         key=lambda x: (
#             source_priority.get(x["source"], 99),
#             x["dateent"] or date.min,
#             x["date"] or date.min,
#             x["source_id"] or 0,
#         )
#     )   
#             # data.sort(
#     #     key=lambda x: (
#     #         x["date"] or date.min,
#     #         x["dateent"] or date.min,
#     #         x["source_id"] or 0,
#     #     )
#     # )

#     # =========================================================
#     # SUMMARY
#     # =========================================================

#     summary = {
#         "opening_cash": ZERO,
#         "opening_bank": ZERO,

#         "closing_cash": ZERO,
#         "closing_bank": ZERO,

#         "total_sales": ZERO,
#         "total_purchase": ZERO,

#         "cash_received": ZERO,
#         "cash_paid": ZERO,

#         "bank_received": ZERO,
#         "bank_paid": ZERO,

#         "total_returns": ZERO,
#         "total_discounts": ZERO,
#         "net_sales": ZERO,

#         "total_collection": ZERO,

#         "qty_sold": ZERO,
#         "total_item_discount": ZERO,
#         "total_invoice_discount": ZERO,

#         "total_debit": ZERO,
#         "total_credit": ZERO,
#         "total_purchase_return":ZERO,
#         "total_sales_return":ZERO,
#     }


#     for row in data:

#         debit = row["debit"] or ZERO
#         credit = row["credit"] or ZERO

#         summary["total_debit"] += debit
#         summary["total_credit"] += credit

#         # =========================================================
#         # SALES
#         # =========================================================

#         if row["source"] == "invoice":
#             summary["total_sales"] += debit if debit > 0 else 0
#             summary["total_sales_return"] += abs(debit) if debit < 0 else 0 

#         # =========================================================
#         # PURCHASE
#         # =========================================================

#         elif row["source"] == "purchase":
#             summary["total_purchase"] += credit if credit > 0 else 0
#             summary["total_purchase_return"] += abs(credit) if credit < 0 else 0

#         # =========================================================
#         # VOUCHERS
#         # =========================================================

#         voucher_amount = debit + credit

#         if row["v_type"] == "CR" and row['credit']>0:
#             summary["cash_received"] += voucher_amount

#         elif row["v_type"] == "CP" and row['credit']>0:
#             summary["cash_paid"] += voucher_amount

#         elif row["v_type"] == "BR" and row['credit']>0:
#             summary["bank_received"] += voucher_amount

#         elif row["v_type"] == "BP" and row['credit']>0:
#             summary["bank_paid"] += voucher_amount


#     # =============================================================
#     # FINAL CALCULATIONS
#     # =============================================================

#     summary["net_sales"] = (
#         summary["total_sales"]
#         - summary["total_returns"]
#         - summary["total_discounts"]
#     )

#     summary["total_collection"] = (
#         summary["cash_received"]
#         + summary["bank_received"]
#     )

#     summary["closing_cash"] = (
#         summary["opening_cash"]
#         + summary["cash_received"]
#         - summary["cash_paid"]
#     )

#     summary["closing_bank"] = (
#         summary["opening_bank"]
#         + summary["bank_received"]
#         - summary["bank_paid"]
#     )

#     return data, columns, summary


def daybook_calc_opening_closing(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'GET required'}, status=405)
        
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    try:
        parsed_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        parsed_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid date format'})

    cash_acc = int(get_default_account('CASH_IN_HAND_ACCOUNT'))
    bank_acc = int(get_default_account('BANK_ACCOUNT'))
    
    def get_account_balance(acc_code, target_date, include_date=False):
        date_filter = 'lte' if include_date else 'lt'
        kwargs_gledg = {f"DATE__{date_filter}": target_date}
        kwargs_inv = {f"date__{date_filter}": target_date}
        
        prev_debit_gledg = Gledg.objects.filter(ACC_CODE=acc_code, AMT_TYPE='DR', **kwargs_gledg).aggregate(total=Sum('AMOUNT'))['total'] or Decimal('0.00')
        prev_credit_gledg = Gledg.objects.filter(ACC_CODE=acc_code, AMT_TYPE='CR', **kwargs_gledg).aggregate(total=Sum('AMOUNT'))['total'] or Decimal('0.00')
        prev_debit_inv = Invoice.objects.filter(header_acc_code=acc_code, is_header=True, **kwargs_inv).aggregate(total=Sum('header_net_total'))['total'] or Decimal('0.00')
        prev_credit_pur = Purchase.objects.filter(header_acc_code=acc_code, is_header=True, **kwargs_inv).aggregate(total=Sum('header_net_total'))['total'] or Decimal('0.00')
        
        running_balance = (prev_debit_gledg + prev_debit_inv) - (prev_credit_gledg + prev_credit_pur)
        
        account = Accounts.objects.filter(ACC_CODE=acc_code).first()
        if account:
            op_bal = Decimal(str(account.OPENING_BALANCE or 0.0))
            bal_type = (account.BALANCE_TYPE or '').strip().upper()
            if bal_type == 'DR':
                running_balance += op_bal
            else:
                running_balance -= op_bal
                
        return running_balance

    op_cash = get_account_balance(cash_acc, parsed_from, include_date=False)
    op_bank = get_account_balance(bank_acc, parsed_from, include_date=False)
    
    cl_cash = get_account_balance(cash_acc, parsed_to, include_date=True)
    cl_bank = get_account_balance(bank_acc, parsed_to, include_date=True)
    
    return JsonResponse({
        'success': True,
        'opening_cash': f"{abs(op_cash):,.2f}",
        'opening_bank': f"{abs(op_bank):,.2f}",
        'closing_cash': f"{abs(cl_cash):,.2f}",
        'closing_bank': f"{abs(cl_bank):,.2f}",
    })

def daybook(request):
    can_view_reports, _ = get_user_perms(request, 'see_reports')
    can_view_daybook, _ = get_user_perms(request, 'view_daybook')
    can_view_own_sales, _ = get_user_perms(request, 'view_own_sales')
    
    if not (can_view_reports or can_view_daybook or can_view_own_sales):
        return redirect('page_not_found')
        
    full_daybook_access = can_view_reports or can_view_daybook

    # =========================================================
    # FEATURES
    # =========================================================
    user = request.user.userprofile
    company = user.company
    branch = user.branch
    terminal = user.terminal

    try:
        features = Features.objects.get(
            user=request.user.username
        )
    except Features.DoesNotExist:

        features = Features.objects.get(
            user="All Features"
        )

    # =========================================================
    # DATES
    # =========================================================

    date_from = (
        request.POST.get("date_from")
        or date.today().isoformat()
    )

    date_to = (
        request.POST.get("date_to")
        or date.today().isoformat()
    )

    v_type = request.POST.get("v_type") or ""

    # =========================================================
    # INVOICE QUERY
    # =========================================================

    invoice_qs = (
        Invoice.objects
        .filter(
            date__range=[
                date_from,
                date_to,
            ],
            is_header=True,
            company=company,
            branch=branch,
            
        )
        .only(
            "id",
            "bill_no",
            "date",
            "dateent",
            "header_acc_code",
            "header_net_total",
            "header_remarks",
        )
        .order_by(
            "date",
            "dateent",
            "id",
        )
    )

    # =========================================================
    # PURCHASE QUERY
    # =========================================================

    purchase_qs = (
        Purchase.objects
        .filter(
            date__range=[
                date_from,
                date_to,
            ],
            is_header=True,
            company=company,
            branch=branch,
        )
        .only(
            "id",
            "bill_no",
            "date",
            "dateent",
            "header_acc_code",
            "header_net_total",
            "header_remarks",
        )
        .order_by(
            "date",
            "dateent",
            "id",
        )
    )

    # =========================================================
    # GLEDG QUERY
    # =========================================================

    gledg_qs = (
        Gledg.objects
        .filter(
            DATE__range=[
                date_from,
                date_to,
            ],
            COMPANY=company,
            BRANCH=branch,
            # SHOW_IN_SALE_RPT = 'Y'
        )
        .only(
            "GLEDG_ID",
            "ACC_CODE",
            "V_TYPE",
            "VNO",
            "DATE",
            "DESCRIPTION",
            "AMOUNT",
            "AMT_TYPE",
            "DATEENT",
        )
        .order_by(
            "DATE",
            "DATEENT",
            "GLEDG_ID",
        )
    )

    # =========================================================
    # VOUCHER TYPE FILTER
    # =========================================================

    if not full_daybook_access:
        invoice_qs = invoice_qs.filter(user=request.user.username)
        purchase_qs = purchase_qs.none()
        gledg_qs = gledg_qs.none()

    if v_type:

        if v_type == "INV":

            purchase_qs = purchase_qs.none()
            gledg_qs = gledg_qs.none()

        elif v_type == "PUR":

            invoice_qs = invoice_qs.none()
            gledg_qs = gledg_qs.none()

        else:

            invoice_qs = invoice_qs.none()
            purchase_qs = purchase_qs.none()

            gledg_qs = gledg_qs.filter(
                V_TYPE=v_type
            )

    # =========================================================
    # BUILD DAYBOOK
    # =========================================================

    data, columns, summary = data_colomun(
        invoice_qs,
        purchase_qs,
        gledg_qs,
    )
    # print('sumary',summary)

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {
        "data": data,
        "columns": columns,
        "date_from": date_from,
        "date_to": date_to,
        "v_type": v_type,
        "features": features,
        "summary": summary,
    }

    return render(
        request,
        "reports/daybook.html",
        context,
    )

    