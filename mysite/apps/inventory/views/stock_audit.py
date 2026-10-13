"""Stock audit UI and zero-value stock adjustment endpoints."""
import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.configuration.selectors import get_default_account_code
from apps.inventory.models import Inventory
from apps.myledger.services.helpers import get_user_perms
from apps.myglobal.services.helpers import get_next_voucher
from apps.purchase.models import Purchase
from apps.sale.models import Invoice

OPENING_STOCK_FALLBACK = 231000001
MAX_AUDIT_ROWS = 50000
ZERO_HEADER_FIELDS = {
    'header_total_items': 0, 'header_item_total': 0, 'header_discount_percent': 0,
    'header_discount_amount': 0, 'header_delivery_charges': 0, 'header_gst_percent': 0,
    'header_gst_amount': 0, 'header_msc_charges': 0, 'header_net_total': 0,
    'header_cash_paid': 0, 'header_bank_paid': 0, 'header_total_paid': 0,
    'header_change_amount': 0,
}


def _scope(request):
    profile = request.user.userprofile
    return profile.company, profile.branch


def _allowed(request):
    try:
        return all(get_user_perms(request, permission)[0]
                   for permission in ('view_inventory', 'edit_item'))
    except Exception:
        return False


@login_required
def stock_audit(request):
    if not _allowed(request):
        return JsonResponse({'error': 'Inventory view and edit permissions are required.'}, status=403)
    return render(request, 'inventory/stock_audit.html')


@login_required
@require_GET
def stock_audit_items(request):
    """Return the complete tenant inventory once; client-side filters/search are instant."""
    if not _allowed(request):
        return JsonResponse({'error': 'Inventory view and edit permissions are required.'}, status=403)
    company, branch = _scope(request)
    base = Inventory.objects.filter(company=company, branch=branch, is_deleted=False)
    # values() avoids N+1 relation queries and avoids instantiating full Inventory models.
    items = base.order_by('prod_name').values(
        'inv_id', 'prod_name', 'alias_name', 'barcode', 'manualbc', 'barcode2', 'bal_qty', 'cost',
        'manufacturer__name', 'product_location', 'category__name', 'subcategory__name',
    )
    rows = [{
        'id': item['inv_id'], 'name': item['prod_name'] or '', 'alias': item['alias_name'] or '',
        'barcode': item['barcode'] or '', 'manual_barcode': item['manualbc'] or '',
        'barcode2': item['barcode2'] or '', 'company': item['manufacturer__name'] or '',
        'location': item['product_location'] or '', 'category': item['category__name'] or '',
        'subcategory': item['subcategory__name'] or '', 'computed_qty': item['bal_qty'] or 0,
        'cost': str(item['cost'] or 0),
    } for item in items.iterator(chunk_size=2000)]
    distinct = lambda field: sorted(set(base.exclude(**{field + '__isnull': True})
                                        .exclude(**{field: ''}).values_list(field, flat=True)), key=str.casefold)
    filter_options = {
        'companies': sorted(set(base.exclude(manufacturer__name__isnull=True)
                                .exclude(manufacturer__name='').values_list('manufacturer__name', flat=True)), key=str.casefold),
        'locations': distinct('product_location'),
        'categories': sorted(set(base.exclude(category__name__isnull=True)
                                 .exclude(category__name='').values_list('category__name', flat=True)), key=str.casefold),
        'subcategories': sorted(set(base.exclude(subcategory__name__isnull=True)
                                     .exclude(subcategory__name='').values_list('subcategory__name', flat=True)), key=str.casefold),
    }
    response = JsonResponse({'rows': rows, 'filters': filter_options, 'count': len(rows)})
    response['Cache-Control'] = 'private, no-store'
    return response


def _build_voucher_rows(model, adjustments, bill_no, opening_account, company, branch,
                        terminal, user, now):
    """Build zero-value rows directly, bypassing sale/purchase price and cost calculations."""
    result = []
    for index, (item, quantity, remarks) in enumerate(adjustments):
        fields = {
            'bill_no': bill_no, 'is_header': index == 0, 'header_edit_count': 0,
            'header_acc_code': opening_account, 'inv_id': item.inv_id,
            'prod_name': item.prod_name or '',
            'category': item.category.name if item.category_id else '',
            'qty': quantity, 'rate': 0, 'uom': item.base_uom.name if item.base_uom_id else '',
            'packing_mode': 1, 'pack_qty': 1, 'row_discount_percent': 0,
            'row_discount_amount': 0, 'row_net_total': 0, 'row_notes': remarks,
            'date': now.date(), 'dateent': now, 'user': user.get_username(),
            'company': company, 'branch': branch, 'posterminal': terminal,
        }
        if model is Invoice:
            fields.update(row_net_cost=0, row_rate_cost=0)
        else:
            fields.update(row_total_cost_per_base_unit=0, row_trade_price=0,
                          row_actual_retail_price=0, row_bonus=0, row_bonus_amount=0,
                          row_fc_rate=0, row_fc_amount=0)
        if index == 0:
            fields.update(ZERO_HEADER_FIELDS)
            fields.update(header_remarks='Stock audit adjustment', header_payment_mode=1)
        else:
            fields['header_total_items'] = 0
        result.append(model(**fields))
    return result


@login_required
@require_POST
@transaction.atomic
def save_stock_audit(request):
    if not _allowed(request):
        return JsonResponse({'error': 'Inventory view and edit permissions are required.'}, status=403)
    try:
        payload = json.loads(request.body.decode('utf-8'))
        entries = payload.get('items') if isinstance(payload, dict) else None
        if not isinstance(entries, list) or not entries or len(entries) > MAX_AUDIT_ROWS:
            raise ValueError(f'Submit between 1 and {MAX_AUDIT_ROWS:,} stock adjustments.')
        parsed = {}
        for row in entries:
            if not isinstance(row, dict):
                raise ValueError('Invalid item row.')
            item_id = row.get('id')
            if type(item_id) is not int or item_id in parsed:
                raise ValueError('Invalid or duplicate item ID.')
            manual_qty = Decimal(str(row.get('manual_qty')))
            if not manual_qty.is_finite() or manual_qty != manual_qty.to_integral_value():
                raise ValueError('Manual quantities must be whole numbers.')
            parsed[item_id] = (int(manual_qty), str(row.get('remarks') or '').strip()[:1000])
    except (ValueError, InvalidOperation, TypeError, UnicodeDecodeError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    company, branch = _scope(request)
    inventory = list(Inventory.objects.select_for_update().select_related('category', 'base_uom').filter(
        company=company, branch=branch, is_deleted=False, inv_id__in=parsed).order_by('inv_id'))
    if len(inventory) != len(parsed):
        return JsonResponse({'error': 'One or more items are not available in this company/branch.'}, status=400)

    sales, purchases = [], []
    for item in inventory:
        manual_qty, remarks = parsed[item.inv_id]
        difference = manual_qty - (item.bal_qty or 0)
        if difference < 0:
            sales.append((item, -difference, remarks))
        elif difference > 0:
            purchases.append((item, difference, remarks))
    if not sales and not purchases:
        return JsonResponse({'success': True, 'adjusted': 0, 'message': 'No quantity differences to adjust.'})

    now = timezone.now()
    opening_account = int(get_default_account_code(
        'default_opening_stock', company.id, branch.id) or OPENING_STOCK_FALLBACK)
    terminal = getattr(request.user.userprofile, 'terminal', None)
    bills = {}
    if sales:
        bill_no = get_next_voucher('INV')
        Invoice.objects.bulk_create(_build_voucher_rows(
            Invoice, sales, bill_no, opening_account, company, branch, terminal, request.user, now), batch_size=1000)
        bills['sale_bill_no'] = bill_no
    if purchases:
        bill_no = get_next_voucher('PUR')
        Purchase.objects.bulk_create(_build_voucher_rows(
            Purchase, purchases, bill_no, opening_account, company, branch, terminal, request.user, now), batch_size=1000)
        bills['purchase_bill_no'] = bill_no

    for item in inventory:
        item.bal_qty = parsed[item.inv_id][0]
        item.updated_at = now
    Inventory.objects.bulk_update(inventory, ['bal_qty', 'updated_at'], batch_size=1000)
    return JsonResponse({'success': True, 'adjusted': len(sales) + len(purchases),
                         'sale_rows': len(sales), 'purchase_rows': len(purchases), **bills})