import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone

from apps.inventory.models import Inventory, StockLot, StockLedger, ItemCategory, ItemSubCategory
from apps.myglobal.services.helpers import get_next_voucher, get_user_perms
from apps.inventory.services.valuation import get_item_valuation, STOCK_IN, STOCK_OUT

# Adjustment types that ADD stock (create StockLot)
INBOUND_ADJ_TYPES = ('OPENING', 'EXCESS_FOUND', 'CORRECTION_IN')
# Adjustment types that REMOVE stock (consume StockLot)
OUTBOUND_ADJ_TYPES = ('DESTROYED_EXPIRED', 'SAMPLE_GIVEN', 'BREAKAGE_LEAKAGE', 'THEFT_SHORTAGE', 'CORRECTION_OUT')
# CORRECTION uses the sign of qty to decide direction


def stock_adjustment_page(request):
    can_view, message = get_user_perms(request, 'stock_update')
    if not can_view:
        return redirect('page_not_found')

    company = request.user.userprofile.company
    branch = request.user.userprofile.branch

    categories = ItemCategory.objects.filter(company=company)
    subcategories = ItemSubCategory.objects.filter(company=company)

    return render(request, 'inventory/stock_adjustment.html', {
        'categories': categories,
        'subcategories': subcategories,
    })


def get_inventory_list(request):
    company = request.user.userprofile.company
    branch = request.user.userprofile.branch

    items = Inventory.objects.filter(company=company, branch=branch, is_deleted=False).values(
        'inv_id', 'prod_name', 'alias_name', 'barcode', 'category_id', 'subcategory_id',
        'product_location', 'bal_qty', 'cost', 'carton_qty'
    )

    return JsonResponse({'success': True, 'items': list(items)})


@transaction.atomic
def save_stock_adjustment(request):
    """
    Save a stock adjustment voucher.
    - Inbound types  (OPENING, EXCESS_FOUND, CORRECTION with +qty) → STOCK_IN
    - Outbound types (DESTROYED_EXPIRED, SAMPLE_GIVEN, etc.)        → STOCK_OUT
    All rows share the same SADJ voucher_no so they can be grouped/reversed together.
    No editing after creation — corrections must be a new voucher.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        default_acc_code = data.get('default_acc_code' or '231000001')  # stored for reference / reporting

        if not items_data:
            return JsonResponse({'success': False, 'message': 'No items to save'})

        company = request.user.userprofile.company
        branch = request.user.userprofile.branch

        voucher_no = get_next_voucher('SADJ')
        current_date = timezone.now().date()

        for item_data in items_data:
            qty = Decimal(str(item_data.get('qty', 0)))
            if qty == 0:
                continue

            inv_id = item_data.get('item_id')
            adj_type = item_data.get('adj_type', 'OPENING')
            acc_code = item_data.get('acc_code', default_acc_code)
            cost_override = item_data.get('cost_override')  # only relevant for OPENING

            if not inv_id:
                continue

            # ─── Determine stock direction ──────────────────────────────
            # OPENING, EXCESS_FOUND, CORRECTION_IN → stock in (positive qty)
            # DESTROYED_EXPIRED, SAMPLE_GIVEN, BREAKAGE_LEAKAGE, etc. → stock out
            # CORRECTION → signed qty decides direction
            if adj_type in INBOUND_ADJ_TYPES:
                is_inbound = True
            elif adj_type in OUTBOUND_ADJ_TYPES:
                is_inbound = False
            elif adj_type == 'CORRECTION':
                is_inbound = qty > 0
            else:
                # Unknown type — treat positive as inbound, negative as outbound
                is_inbound = qty > 0

            # ─── Determine unit cost ────────────────────────────────────
            if adj_type == 'OPENING' and cost_override is not None:
                # User explicitly entered cost per base unit for opening stock
                unit_cost = Decimal(str(cost_override))
            elif is_inbound:
                # For other inbound (EXCESS_FOUND, CORRECTION+), use stored last_pur_price
                try:
                    inv_item = Inventory.objects.only('last_pur_price', 'cost').get(
                        inv_id=inv_id, company=company, branch=branch
                    )
                    unit_cost = inv_item.last_pur_price or inv_item.cost or Decimal('0')
                except Inventory.DoesNotExist:
                    unit_cost = Decimal('0')
            else:
                # For outbound, estimate from valuation engine (read-only, no writes)
                _total_cost, unit_cost, _batches = get_item_valuation(
                    item_id=inv_id,
                    qty=abs(qty),
                    company_id=company.id,
                    branch_id=branch.id,
                )

            # ─── Call correct valuation function ────────────────────────
            if is_inbound:
                STOCK_IN(
                    company_id=company.id,
                    branch_id=branch.id,
                    inventory_item_id=inv_id,
                    base_quantity=abs(qty),
                    rate_cost_per_unit=unit_cost,
                    voucher_date=current_date,
                    voucher_type='ADJUSTMENT',
                    voucher_bill_no=voucher_no,
                    voucher_row_id=None,
                    expiry_date=None,
                    is_update=False,
                    adj_type=adj_type,
                    acc_code = acc_code or default_acc_code
                )
                # For OPENING with explicit cost, also stamp last_pur_price + cost on Inventory
                if adj_type == 'OPENING' and cost_override is not None:
                    Inventory.objects.filter(
                        inv_id=inv_id, company=company, branch=branch
                    ).update(last_pur_price=unit_cost, cost=unit_cost)
            else:
                STOCK_OUT(
                    company_id=company.id,
                    branch_id=branch.id,
                    inventory_item_id=inv_id,
                    base_quantity_required=abs(qty),
                    voucher_date=current_date,
                    voucher_type='ADJUSTMENT',
                    voucher_bill_no=voucher_no,
                    voucher_row_id=None,
                    is_update=False,
                    adj_type=adj_type,
                    acc_code = acc_code or default_acc_code
                )

        return JsonResponse({
            'success': True,
            'message': f'Adjustment saved with Voucher #{voucher_no}',
            'voucher_no': voucher_no,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)})
