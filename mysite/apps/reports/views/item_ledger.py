from django.shortcuts import render
from datetime import date
from django.views.decorators.csrf import csrf_exempt
import json

from apps.myglobal.services.helpers import get_user_perms
from apps.purchase.models import Purchase
from apps.sale.models import Invoice
from apps.inventory.models import Inventory
from apps.myaccounts.models import Accounts

@csrf_exempt
def item_ledger(request):
    has_perm, _ = get_user_perms(request, 'view_stock_report')
    has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
    date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
    date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
    inv_id = request.POST.get('inv_id') or request.GET.get('inv_id')
    print('invid',inv_id)
    
    data = []
    
    if inv_id:
        try:
            inv_id = int(inv_id)
        except ValueError:
            inv_id = None
            
    if inv_id:
        # Fetch purchases
        purchases = Purchase.objects.filter(
            inv_id=inv_id,  date__range=[date_from, date_to]
        ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
        # Fetch sales
        sales = Invoice.objects.filter(
            inv_id=inv_id,  date__range=[date_from, date_to]
        ).values('date', 'header_acc_code', 'bill_no', 'qty', 'pack_qty', 'rate')
        
        # Collect account codes to fetch names in one query
        acc_codes = set()
        for p in purchases:
            if p['header_acc_code']: acc_codes.add(p['header_acc_code'])
        for s in sales:
            if s['header_acc_code']: acc_codes.add(s['header_acc_code'])
            
        accounts = Accounts.objects.filter(ACC_CODE__in=acc_codes).values('ACC_CODE', 'ACC_NAME')
        acc_dict = {a['ACC_CODE']: (a['ACC_NAME'] or f"Account {a['ACC_CODE']}") for a in accounts}
        
        # Process Purchases
        for p in purchases:
            qty = float(p['qty'] or 0)
            pack_qty = float(p['pack_qty'] or 1)
            # If pack_qty is exactly 0 but qty is not, it implies pack_qty is not used, so fallback to 1.
            if pack_qty == 0: pack_qty = 1 
            
            data.append({
                'date': p['date'].isoformat() if p['date'] else '',
                'v_type': 'PUR',
                'account_name': acc_dict.get(p['header_acc_code'], 'Unknown'),
                'bill_no': f"PUR-{p['bill_no']}",
                'qty_in': qty * pack_qty,
                'qty_out': 0.0,
                'cost_rate': float(p['rate'] or 0) if has_cost_perm else 0.0,
                'sale_rate': 0.0,
                'sort_date': p['date'] or date.min
            })
            
        # Process Sales
        for s in sales:
            qty = float(s['qty'] or 0)
            pack_qty = float(s['pack_qty'] or 1)
            if pack_qty == 0: pack_qty = 1 
            
            data.append({
                'date': s['date'].isoformat() if s['date'] else '',
                'v_type': 'INV',
                'account_name': acc_dict.get(s['header_acc_code'], 'Unknown'),
                'bill_no': f"INV-{s['bill_no']}",
                'qty_in': 0.0,
                'qty_out': qty * pack_qty,
                'cost_rate': 0.0,
                'sale_rate': float(s['rate'] or 0),
                'sort_date': s['date'] or date.min
            })
            
        # Sort chronologically
        data.sort(key=lambda x: x['sort_date'])
        
    # Get all items for dropdown (lightweight fetch)
    items = Inventory.objects.filter(is_deleted=False).values('inv_id', 'prod_name', 'barcode')
    items_list = list(items)
    
    # Calculate running balance if data exists
    running_balance = 0.0
    for row in data:
        running_balance += row['qty_in'] - row['qty_out']
        row['balance'] = running_balance

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'inv_id': inv_id or '',
        'data': data,
        'has_cost_perm': has_cost_perm,
        'selected_item_name': items.filter(inv_id=inv_id).first()['prod_name'] if inv_id else ''
    }
    
    return render(request, 'reports/item_ledger.html', context)
