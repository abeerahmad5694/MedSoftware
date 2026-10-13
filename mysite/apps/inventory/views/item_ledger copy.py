

from apps.inventory.services.valuation import _get_valuation_method
from django.shortcuts import render
from datetime import date
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum

from apps.inventory.models import Inventory, StockLedger
from apps.purchase.models import Purchase
from apps.sale.models import Invoice
from apps.myglobal.services.helpers import get_user_perms
from apps.myaccounts.models import Accounts
from apps.configuration.models import CompanyConfiguration

# def _get_method(company_id, branch_id):
#     try:
#         return CompanyConfiguration.objects.only('stock_valuation_method').get(
#             company_id=company_id, branch_id=branch_id
#         ).stock_valuation_method or 'LAST_PUR_PRICE'
#     except:
#         return 'LAST_PUR_PRICE'

@csrf_exempt
def item_ledger(request):
    has_perm, _ = get_user_perms(request, 'view_stock_report')
    has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
    date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
    date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
    inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
    
    try:
        inv_id = int(inv_id)
    except:
        inv_id = None

    data = []
    opening_balance = 0
    opening_value = 0

    method = _get_valuation_method(request.user.userprofile.company_id, request.user.userprofile.branch_id)

    if inv_id:
        if method == 'LAST_PUR_PRICE':
            # ===== OLD LOGIC + ADJUSTMENT =====
            purchases = Purchase.objects.filter(
                inv_id=inv_id, date__range=[date_from, date_to]
            ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
            
            sales = Invoice.objects.filter(
                inv_id=inv_id, date__range=[date_from, date_to]
            ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')

            # 1. Also get ADJUSTMENT from StockLedger for old logic
            adjustments = StockLedger.objects.filter(
                inventory_item_id=inv_id,
                voucher_type='ADJUSTMENT',
                voucher_date__range=[date_from, date_to]
            ).select_related('stock_lot').order_by('voucher_date', 'id')

            # Opening for old logic = PUR - SALE + ADJ before date_from
            opening_pur = Purchase.objects.filter(inv_id=inv_id, date__lt=date_from).aggregate(s=Sum('qty'))['s'] or 0
            opening_sale = Invoice.objects.filter(inv_id=inv_id, date__lt=date_from).aggregate(s=Sum('qty'))['s'] or 0
            opening_adj = StockLedger.objects.filter(
                inventory_item_id=inv_id, voucher_type='ADJUSTMENT', voucher_date__lt=date_from
            ).aggregate(s=Sum('base_quantity'))['s'] or 0
            opening_balance = float(opening_pur - opening_sale + opening_adj)

            # Accounts for all 3 types
            acc_codes = set(p['header_acc_code'] for p in purchases if p['header_acc_code']) | \
                        set(s['header_acc_code'] for s in sales if s['header_acc_code']) | \
                        set(a.acc_code for a in adjustments if a.acc_code)
            acc_dict = {a['ACC_CODE']: a['ACC_NAME'] for a in Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE','ACC_NAME')}

            for p in purchases:
                qty = float(p['qty'] or 0) * float(p['pack_qty'] or 1)
                data.append({
                    'date': p['date'].isoformat() if p['date'] else '',
                    'v_type': 'PUR',
                    'bill_no': f"PUR-{p['bill_no']}",
                    'account_name': acc_dict.get(p['header_acc_code'], ''),
                    'qty_in': qty, 'qty_out': 0,
                    'cost_rate': float(p['rate'] or 0) if has_cost_perm else 0,
                    'sort_date': p['date'] or date.min
                })
            for s in sales:
                qty = float(s['qty'] or 0) * float(s['pack_qty'] or 1)
                data.append({
                    'date': s['date'].isoformat() if s['date'] else '',
                    'v_type': 'INV',
                    'bill_no': f"INV-{s['bill_no']}",
                    'account_name': acc_dict.get(s['header_acc_code'], ''),
                    'qty_in': 0, 'qty_out': qty,
                    'cost_rate': 0,
                    'sort_date': s['date'] or date.min
                })
            # ADJUSTMENT rows from StockLedger
            for led in adjustments:
                qty = float(led.base_quantity or 0)
                data.append({
                    'date': led.voucher_date.isoformat(),
                    'v_type': f"ADJ-{led.adj_type}" if led.adj_type else "ADJUSTMENT",
                    'bill_no': f"ADJ-{led.voucher_bill_no}",
                    'account_name': acc_dict.get(led.acc_code, str(led.acc_code or '')),
                    'adj_type': led.adj_type or '',
                    'qty_in': qty if qty > 0 else 0,
                    'qty_out': abs(qty) if qty < 0 else 0,
                    'cost_rate': float(led.rate_cost_per_unit or 0) if has_cost_perm else 0,
                    'sort_date': led.voucher_date,
                })

            data.sort(key=lambda x: x['sort_date'])
            running = opening_balance
            for row in data:
                running += row['qty_in'] - row['qty_out']
                row['balance'] = running

        else:
            # ===== NEW LOGIC - your current code as is =====
            opening_agg = StockLedger.objects.filter(
                inventory_item_id=inv_id, voucher_date__lt=date_from
            ).aggregate(qty=Sum('base_quantity'), val=Sum('net_value'))
            opening_balance = float(opening_agg['qty'] or 0)
            opening_value = float(opening_agg['val'] or 0)

            ledgers = StockLedger.objects.filter(
                inventory_item_id=inv_id, voucher_date__range=[date_from, date_to]
            ).select_related('stock_lot').order_by('voucher_date', 'id')

            acc_codes = set(l.acc_code for l in ledgers if l.acc_code)
            acc_dict = {a['ACC_CODE']: a['ACC_NAME'] for a in Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE','ACC_NAME')}

            running_balance = opening_balance
            running_value = opening_value
            for led in ledgers:
                qty = float(led.base_quantity or 0)
                running_balance += qty
                running_value += float(led.net_value or 0)
                v_type_display = f"ADJ-{led.adj_type}" if led.voucher_type == 'ADJUSTMENT' and led.adj_type else led.voucher_type
                data.append({
                    'date': led.voucher_date.isoformat(),
                    'v_type': v_type_display,
                    'bill_no': f"{led.voucher_type}-{led.voucher_bill_no}",
                    'account_name': acc_dict.get(led.acc_code, ''),
                    'adj_type': led.adj_type or '',
                    'qty_in': qty if qty > 0 else 0,
                    'qty_out': abs(qty) if qty < 0 else 0,
                    'cost_rate': float(led.rate_cost_per_unit or 0) if has_cost_perm else 0,
                    'net_value': float(led.net_value or 0),
                    'balance': running_balance,
                    'balance_value': running_value,
                    'sort_date': led.voucher_date,
                })

    items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
    return render(request, 'inventory/item_ledger.html', {
        'date_from': date_from, 'date_to': date_to,
        'inv_id': inv_id or '', 'data': data,
        'opening_balance': opening_balance, 'opening_value': opening_value,
        'has_cost_perm': has_cost_perm, 'items_list': list(items),
        'method': method
    })
    
    
    


# from apps.inventory.services.valuation import _get_valuation_method
# from django.shortcuts import render
# from datetime import date
# from django.views.decorators.csrf import csrf_exempt
# import json
# from django.db.models import Sum

# from apps.inventory.models import Inventory, StockLot, StockLedger
# from apps.myglobal.services.helpers import get_user_perms
# from apps.myaccounts.models import Accounts
# from apps.purchase.models import Purchase
# from apps.sale.models import Invoice


# @csrf_exempt
# def item_ledger(request):
#     has_perm, _ = get_user_perms(request, 'view_stock_report')
#     has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
#     date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
#     date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
#     inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
    
#     # GET company method
#     company_id = request.user.userprofile.company_id
#     branch_id = request.user.userprofile.branch_id
    
#     method = _get_valuation_method(company_id, branch_id)

#     try:
#         inv_id = int(inv_id)
#     except:
#         inv_id = None

#     data = []
#     opening_balance = 0
#     opening_value = 0

#     if not inv_id:
#         items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
#         return render(request, 'inventory/item_ledger.html', {
#             'date_from': date_from, 'date_to': date_to,
#             'inv_id': '', 'data': [], 'opening_balance': 0,
#             'items_list': list(items), 'has_cost_perm': has_cost_perm
#         })

#     # ===================== CONDITION =====================
#     if method == 'LAST_PUR_PRICE':
#         # ===== OLD LOGIC - Purchase + Invoice direct =====
#         purchases = Purchase.objects.filter(
#             inv_id=inv_id, date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         sales = Invoice.objects.filter(
#             inv_id=inv_id, date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         acc_codes = set(p['header_acc_code'] for p in purchases if p['header_acc_code']) | \
#                     set(s['header_acc_code'] for s in sales if s['header_acc_code'])
#         acc_dict = {a['ACC_CODE']: a['ACC_NAME'] for a in Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE','ACC_NAME')}

#         for p in purchases:
#             qty = float(p['qty'] or 0) * float(p['pack_qty'] or 1)
#             data.append({
#                 'date': p['date'].isoformat() if p['date'] else '',
#                 'v_type': 'PUR',
#                 'bill_no': f"PUR-{p['bill_no']}",
#                 'account_name': acc_dict.get(p['header_acc_code'], ''),
#                 'qty_in': qty, 'qty_out': 0,
#                 'cost_rate': float(p['rate'] or 0) if has_cost_perm else 0,
#                 'balance': 0, 'sort_date': p['date'] or date.min
#             })
#         for s in sales:
#             qty = float(s['qty'] or 0) * float(s['pack_qty'] or 1)
#             data.append({
#                 'date': s['date'].isoformat() if s['date'] else '',
#                 'v_type': 'INV',
#                 'bill_no': f"INV-{s['bill_no']}",
#                 'account_name': acc_dict.get(s['header_acc_code'], ''),
#                 'qty_in': 0, 'qty_out': qty,
#                 'cost_rate': 0, 'balance': 0,
#                 'sort_date': s['date'] or date.min
#             })
#         data.sort(key=lambda x: x['sort_date'])
#         running = 0
#         for row in data:
#             running += row['qty_in'] - row['qty_out']
#             row['balance'] = running

#     else:
#         # ===== NEW LOGIC - StockLedger + StockLot =====
#         opening_agg = StockLedger.objects.filter(
#             inventory_item_id=inv_id, voucher_date__lt=date_from
#         ).aggregate(qty=Sum('base_quantity'), val=Sum('net_value'))
#         opening_balance = float(opening_agg['qty'] or 0)
#         opening_value = float(opening_agg['val'] or 0)

#         ledgers = StockLedger.objects.filter(
#             inventory_item_id=inv_id, voucher_date__range=[date_from, date_to]
#         ).select_related('stock_lot').order_by('voucher_date', 'id')

#         acc_codes = set(l.acc_code for l in ledgers if l.acc_code)
#         acc_dict = {a['ACC_CODE']: a['ACC_NAME'] for a in Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE','ACC_NAME')}

#         running_balance = opening_balance
#         running_value = opening_value
#         for led in ledgers:
#             qty = float(led.base_quantity or 0)
#             running_balance += qty
#             running_value += float(led.net_value or 0)
#             v_type_display = led.voucher_type
#             if led.voucher_type == 'ADJUSTMENT' and led.adj_type:
#                 v_type_display = f"ADJ-{led.adj_type}"

#             data.append({
#                 'date': led.voucher_date.isoformat(),
#                 'v_type': v_type_display,
#                 'bill_no': f"{led.voucher_type}-{led.voucher_bill_no}",
#                 'account_name': acc_dict.get(led.acc_code, str(led.acc_code or '')),
#                 'qty_in': qty if qty > 0 else 0,
#                 'qty_out': abs(qty) if qty < 0 else 0,
#                 'cost_rate': float(led.rate_cost_per_unit or 0) if has_cost_perm else 0,
#                 'net_value': float(led.net_value or 0),
#                 'balance': running_balance,
#                 'balance_value': running_value,
#                 'sort_date': led.voucher_date,
#                 'id': led.id,
#             })

#     items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
#     return render(request, 'inventory/item_ledger.html', {
#         'date_from': date_from, 'date_to': date_to,
#         'inv_id': inv_id, 'data': data,
#         'opening_balance': opening_balance, 'opening_value': opening_value,
#         'has_cost_perm': has_cost_perm, 'items_list': list(items),
#         'method': method # for debug in template
#     })
    
    
    
# @csrf_exempt
# def item_ledger(request):
#     has_perm, _ = get_user_perms(request, 'view_stock_report')
#     has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
#     date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
#     date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
#     inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
    
#     data = []
#     opening_balance = 0
#     opening_value = 0
    
#     if inv_id:
#         try:
#             inv_id = int(inv_id)
#         except:
#             inv_id = None
            
#     if inv_id:
#         # 1. Opening balance before date_from
#         opening_agg = StockLedger.objects.filter(
#             inventory_item_id=inv_id,
#             voucher_date__lt=date_from
#         ).aggregate(
#             qty=Sum('base_quantity'),
#             val=Sum('net_value')
#         )
#         opening_balance = float(opening_agg['qty'] or 0)
#         opening_value = float(opening_agg['val'] or 0)

#         # 2. All ledger entries in range - SINGLE QUERY O(N)
#         ledgers = StockLedger.objects.filter(
#             inventory_item_id=inv_id,
#             voucher_date__range=[date_from, date_to]
#         ).select_related('stock_lot').order_by('voucher_date', 'id')

#         # Collect acc_codes for account names
#         acc_codes = set(l.acc_code for l in ledgers if l.acc_code)
#         accounts = Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE', 'ACC_NAME')
#         acc_dict = {a['ACC_CODE']: a['ACC_NAME'] for a in accounts}

#         running_balance = opening_balance
#         running_value = opening_value

#         for led in ledgers:
#             qty = float(led.base_quantity or 0)
#             running_balance += qty
#             running_value += float(led.net_value or 0)

#             # Determine display type
#             v_type_display = led.voucher_type
#             if led.voucher_type == 'ADJUSTMENT' and led.adj_type:
#                 v_type_display = f"ADJ-{led.adj_type}"  # ADJ-OPENING, ADJ-CORRECTION etc

#             data.append({
#                 'date': led.voucher_date.isoformat(),
#                 'v_type': v_type_display,
#                 'bill_no': f"{led.voucher_type}-{led.voucher_bill_no}",
#                 'account_name': acc_dict.get(led.acc_code, str(led.acc_code or '')),
#                 'adj_type': led.adj_type or '',
#                 'acc_code': led.acc_code or '',
#                 'lot_id': led.stock_lot_id or '',
#                 'lot_cost': float(led.stock_lot.rate_cost_per_unit) if led.stock_lot else 0,
#                 'qty_in': qty if qty > 0 else 0,
#                 'qty_out': abs(qty) if qty < 0 else 0,
#                 'cost_rate': float(led.rate_cost_per_unit or 0) if has_cost_perm else 0,
#                 'net_value': float(led.net_value or 0),
#                 'balance': running_balance,
#                 'balance_value': running_value,
#                 'sort_date': led.voucher_date,
#                 'id': led.id,
#             })

#     items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')

#     context = {
#         'date_from': date_from,
#         'date_to': date_to,
#         'inv_id': inv_id or '',
#         'data': data,
#         'opening_balance': opening_balance,
#         'opening_value': opening_value,
#         'has_cost_perm': has_cost_perm,
#         'items_list': list(items),
#     }
    
#     return render(request, 'inventory/item_ledger.html', context)












# from django.shortcuts import render
# from datetime import date
# from django.views.decorators.csrf import csrf_exempt
# import json

# from apps.myglobal.services.helpers import get_user_perms
# from apps.purchase.models import Purchase
# from apps.sale.models import Invoice
# from apps.inventory.models import Inventory
# from apps.myaccounts.models import Accounts

# @csrf_exempt
# def item_ledger(request):
#     has_perm, _ = get_user_perms(request, 'view_stock_report')
#     has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
#     date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
#     date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
#     inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
#     print('invid',inv_id)
    
#     data = []
    
#     if inv_id:
#         try:
#             inv_id = int(inv_id)
#         except ValueError:
#             inv_id = None
            
#     if inv_id:
#         # Fetch purchases
#         purchases = Purchase.objects.filter(
#             inv_id=inv_id,  date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         # Fetch sales
#         sales = Invoice.objects.filter(
#             inv_id=inv_id,  date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         # Collect account codes to fetch names in one query
#         acc_codes = set()
#         for p in purchases:
#             if p['header_acc_code']: acc_codes.add(p['header_acc_code'])
#         for s in sales:
#             if s['header_acc_code']: acc_codes.add(s['header_acc_code'])
            
#         accounts = Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE', 'ACC_NAME')
#         acc_dict = {a['ACC_CODE']: (a['ACC_NAME'] or f"Account {a['ACC_CODE']}") for a in accounts}
        
#         # Process Purchases
#         for p in purchases:
#             qty = float(p['qty'] or 0)
#             pack_qty = float(p['pack_qty'] or 1)
#             # If pack_qty is exactly 0 but qty is not, it implies pack_qty is not used, so fallback to 1.
#             if pack_qty == 0: pack_qty = 1 
            
#             data.append({
#                 'date': p['date'].isoformat() if p['date'] else '',
#                 'v_type': 'PUR',
#                 'account_name': acc_dict.get(p['header_acc_code'], 'Unknown'),
#                 'bill_no': f"PUR-{p['bill_no']}",
#                 'qty_in': qty * pack_qty,
#                 'qty_out': 0.0,
#                 'cost_rate': float(p['rate'] or 0) if has_cost_perm else 0.0,
#                 'sale_rate': 0.0,
#                 'sort_date': p['date'] or date.min
#             })
            
#         # Process Sales
#         for s in sales:
#             qty = float(s['qty'] or 0)
#             pack_qty = float(s['pack_qty'] or 1)
#             if pack_qty == 0: pack_qty = 1 
            
#             data.append({
#                 'date': s['date'].isoformat() if s['date'] else '',
#                 'v_type': 'INV',
#                 'account_name': acc_dict.get(s['header_acc_code'], 'Unknown'),
#                 'bill_no': f"INV-{s['bill_no']}",
#                 'qty_in': 0.0,
#                 'qty_out': qty * pack_qty,
#                 'cost_rate': 0.0,
#                 'sale_rate': float(s['rate'] or 0),
#                 'sort_date': s['date'] or date.min
#             })
            
#         # Sort chronologically
#         data.sort(key=lambda x: x['sort_date'])
        
#     # Get all items for dropdown (lightweight fetch)
#     items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
#     items_list = list(items)
    
#     # Calculate running balance if data exists
#     running_balance = 0.0
#     for row in data:
#         running_balance += row['qty_in'] - row['qty_out']
#         row['balance'] = running_balance

#     context = {
#         'date_from': date_from,
#         'date_to': date_to,
#         'inv_id': inv_id or '',
#         'data': data,
#         'has_cost_perm': has_cost_perm,
#         'selected_item_name': items.filter(inv_id=inv_id).first()['prod_name'] if inv_id else ''
#     }
    
#     return render(request, 'reports/item_ledger.html', context)









# from django.shortcuts import render
# from datetime import date
# from django.views.decorators.csrf import csrf_exempt
# import json

# from apps.myglobal.services.helpers import get_user_perms
# from apps.purchase.models import Purchase
# from apps.sale.models import Invoice
# from apps.inventory.models import Inventory
# from apps.myaccounts.models import Accounts

# @csrf_exempt
# def item_ledger(request):
#     has_perm, _ = get_user_perms(request, 'view_stock_report')
#     has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
#     date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
#     date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
#     inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
#     print('invid',inv_id)
    
#     data = []
    
#     if inv_id:
#         try:
#             inv_id = int(inv_id)
#         except ValueError:
#             inv_id = None
            
#     if inv_id:
#         # Fetch purchases
#         purchases = Purchase.objects.filter(
#             inv_id=inv_id,  date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         # Fetch sales
#         sales = Invoice.objects.filter(
#             inv_id=inv_id,  date__range=[date_from, date_to]
#         ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
#         # Collect account codes to fetch names in one query
#         acc_codes = set()
#         for p in purchases:
#             if p['header_acc_code']: acc_codes.add(p['header_acc_code'])
#         for s in sales:
#             if s['header_acc_code']: acc_codes.add(s['header_acc_code'])
            
#         accounts = Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE', 'ACC_NAME')
#         acc_dict = {a['ACC_CODE']: (a['ACC_NAME'] or f"Account {a['ACC_CODE']}") for a in accounts}
        
#         # Process Purchases
#         for p in purchases:
#             qty = float(p['qty'] or 0)
#             pack_qty = float(p['pack_qty'] or 1)
#             # If pack_qty is exactly 0 but qty is not, it implies pack_qty is not used, so fallback to 1.
#             if pack_qty == 0: pack_qty = 1 
            
#             data.append({
#                 'date': p['date'].isoformat() if p['date'] else '',
#                 'v_type': 'PUR',
#                 'account_name': acc_dict.get(p['header_acc_code'], 'Unknown'),
#                 'bill_no': f"PUR-{p['bill_no']}",
#                 'qty_in': qty * pack_qty,
#                 'qty_out': 0.0,
#                 'cost_rate': float(p['rate'] or 0) if has_cost_perm else 0.0,
#                 'sale_rate': 0.0,
#                 'sort_date': p['date'] or date.min
#             })
            
#         # Process Sales
#         for s in sales:
#             qty = float(s['qty'] or 0)
#             pack_qty = float(s['pack_qty'] or 1)
#             if pack_qty == 0: pack_qty = 1 
            
#             data.append({
#                 'date': s['date'].isoformat() if s['date'] else '',
#                 'v_type': 'INV',
#                 'account_name': acc_dict.get(s['header_acc_code'], 'Unknown'),
#                 'bill_no': f"INV-{s['bill_no']}",
#                 'qty_in': 0.0,
#                 'qty_out': qty * pack_qty,
#                 'cost_rate': 0.0,
#                 'sale_rate': float(s['rate'] or 0),
#                 'sort_date': s['date'] or date.min
#             })
            
#         # Sort chronologically
#         data.sort(key=lambda x: x['sort_date'])
        
#     # Get all items for dropdown (lightweight fetch)
#     items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
#     items_list = list(items)
    
#     # Calculate running balance if data exists
#     running_balance = 0.0
#     for row in data:
#         running_balance += row['qty_in'] - row['qty_out']
#         row['balance'] = running_balance

#     context = {
#         'date_from': date_from,
#         'date_to': date_to,
#         'inv_id': inv_id or '',
#         'data': data,
#         'has_cost_perm': has_cost_perm,
#         'selected_item_name': items.filter(inv_id=inv_id).first()['prod_name'] if inv_id else ''
#     }
    
#     return render(request, 'inventory/item_ledger.html', context)
