from django.shortcuts import render
from datetime import date
from django.db.models import Sum, DecimalField , F
from django.db.models.functions import Coalesce
from django.views.decorators.csrf import csrf_exempt
import json

from apps.myglobal.services.helpers import get_user_perms
from apps.purchase.models import Purchase
from apps.sale.models import Invoice
from apps.inventory.models import Inventory

@csrf_exempt
def stock_report(request):
    # Check permissions
    has_perm, _ = get_user_perms(request, 'view_stock_report')
    # Can optionally enforce this:
    # if not has_perm: return render(request, '403.html')
    
    has_cost_perm, _ = get_user_perms(request, 'see_cost_in_reports')
    
    date_from = request.POST.get('date_from') or request.GET.get('date_from') or date.today().isoformat()
    date_to = request.POST.get('date_to') or request.GET.get('date_to') or date.today().isoformat()
    
    # Purchases (O(n) db aggregation)
    purchases = Purchase.objects.filter(
         date__range=[date_from, date_to]
    ).values('inv_id').annotate(
        pur_qty=Coalesce(Sum(F('qty')*F('pack_qty')), 0.0, output_field=DecimalField()),
        pur_val=Coalesce(Sum('row_net_total'), 0.0, output_field=DecimalField())
    )
    pur_dict = {p['inv_id']: p for p in purchases if p['inv_id']}
    
    # Sales (O(n) db aggregation)
    sales = Invoice.objects.filter(
         date__range=[date_from, date_to]
    ).values('inv_id').annotate(
        sale_qty=Coalesce(Sum(F('qty')*F('pack_qty')), 0.0, output_field=DecimalField()),
        sale_val=Coalesce(Sum('row_net_total'), 0.0, output_field=DecimalField())
    )
    sale_dict = {s['inv_id']: s for s in sales if s['inv_id']}
    
    items = Inventory.objects.filter(is_deleted=False).select_related('company', 'category')
    
    data = []
    
    for item in items:
        pur = pur_dict.get(item.inv_id, {})
        sale = sale_dict.get(item.inv_id, {})
        
        pur_qty = float(pur.get('pur_qty') or 0)
        pur_val = float(pur.get('pur_val') or 0)
        
        sale_qty = float(sale.get('sale_qty') or 0)
        sale_val = float(sale.get('sale_val') or 0)
        
        avg_pur_rate = round(pur_val / pur_qty, 2) if pur_qty > 0 else 0
        avg_sale_rate = round(sale_val / sale_qty, 2) if sale_qty > 0 else 0
        
        if not has_cost_perm:
            pur_qty = 0
            avg_pur_rate = 0
            
        bal_qty = float(item.bal_qty or 0)
        
        data.append({
            'inv_id': item.inv_id,
            'prod_name': item.prod_name or '',
            'company': item.company.name if item.company else '',
            'category': item.category.name if item.category else '',
            'pur_qty': pur_qty,
            'avg_pur_rate': avg_pur_rate,
            'sale_qty': sale_qty,
            'avg_sale_rate': avg_sale_rate,
            'bal_qty': bal_qty,
        })
        
    # Serialize for frontend filtering O(n) rendering
    data_json = json.dumps(data)

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'data_json': data_json,
        'has_cost_perm': has_cost_perm,
    }
    
    return render(request, 'reports/stock_report.html', context)
