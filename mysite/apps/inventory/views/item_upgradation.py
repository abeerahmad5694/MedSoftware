import json
from decimal import Decimal
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.models import User

from apps.inventory.models import Inventory, StockLot, StockLedger
from apps.myglobal.services.helpers import get_next_voucher
from apps.inventory.services.valuation import STOCK_IN, STOCK_OUT
from apps.configuration.selectors import get_default_account_code
from apps.myaccounts.models import Accounts
from apps.myledger.services.dto import GledgLineDTO
from apps.myledger.services.voucher_utills import create_gledg_entries


def item_upgradation_page(request):
    """
    Renders the Item Upgradation & Assembly screen.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    user_profile = getattr(request.user, 'userprofile', None)
    company = getattr(user_profile, 'company', None)
    branch = getattr(user_profile, 'branch', None)

    # Fetch technician / staff names for dropdown
    technicians_qs = User.objects.filter(is_active=True).values('id', 'first_name', 'last_name', 'username')
    technicians = []
    for u in technicians_qs:
        name = f"{u['first_name']} {u['last_name']}".strip() or u['username']
        if name and name not in technicians:
            technicians.append(name)

    default_cash_acc = get_default_account_code('default_cash_acc', company.id if company else None, branch.id if branch else None) or 110000001
    acc_obj = Accounts.objects.filter(ACC_CODE=default_cash_acc).first()
    default_cash_acc_name = acc_obj.ACC_NAME if acc_obj else 'Cash in Hand'

    context = {
        'technicians': technicians,
        'current_user_name': request.user.get_full_name() or request.user.username,
        'company': company,
        'branch': branch,
        'default_cash_acc': default_cash_acc,
        'default_cash_acc_name': default_cash_acc_name,
    }
    return render(request, 'inventory/item_upgradation.html', context)


def search_item_by_serial_or_barcode(request):
    """
    Quick search endpoint for top search box.
    Matches serial_no, serial_no2, barcode, alias_name, or inv_id.
    """
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'success': False, 'message': 'Search query is required'})

    user_profile = getattr(request.user, 'userprofile', None)
    company = getattr(user_profile, 'company', None)
    branch = getattr(user_profile, 'branch', None)

    filters = Q(is_deleted=False)
    if company:
        filters &= Q(company=company)

    # Primary search
    exact_q = (
        Q(serial_no__iexact=q) |
        Q(serial_no2__iexact=q) |
        Q(barcode__iexact=q) |
        Q(alias_name__iexact=q)
    )
    if q.isdigit():
        exact_q |= Q(inv_id=int(q))

    item = Inventory.objects.filter(filters & exact_q).first()

    # Fallback search by icontains
    if not item:
        item = Inventory.objects.filter(
            filters & (Q(serial_no__icontains=q) | Q(prod_name__icontains=q))
        ).first()

    if not item:
        return JsonResponse({'success': False, 'message': f'No item found for "{q}"'})

    bought_cost = float(item.individual_cost or item.cost or item.last_pur_price or 0)
    extra_cost = float(item.extra_cost or 0)
    final_cost = bought_cost + extra_cost

    return JsonResponse({
        'success': True,
        'item': {
            'inv_id': item.inv_id,
            'prod_name': item.prod_name,
            'serial_no': item.serial_no or '',
            'serial_no2': item.serial_no2 or '',
            'processor': item.processor or '',
            'ram': item.ram or '',
            'storage': item.storage or '',
            'color': item.color or '',
            'model_year': item.model_year or '',
            'condition': item.condition or 'NEW',
            'status': item.status or 'IN_STOCK',
            'bought_cost': bought_cost,
            'extra_cost': extra_cost,
            'final_cost': final_cost,
            'bal_qty': float(item.bal_qty or 0),
            'is_variant': item.is_variant,
            'tracking_type': item.tracking_type or 'NONE',
        }
    })


@transaction.atomic
def save_item_upgradation(request):
    """
    Saves an Item Upgradation / Assembly / Repair voucher.
    - Parts IN: deducted via STOCK_OUT (adj_type='ITEM_MAINTENANCE') with upgrade_no and linked_item.
    - Parts OUT (Return to Stock): put back via STOCK_IN (adj_type='ITEM_MAINTENANCE') with upgrade_no and linked_item.
    - Assembly Mode: Finished product is stocked in via STOCK_IN at accumulated cost.
    - Updates main_item.extra_cost and optional spec upgrades (RAM, Storage, Condition).
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required'}, status=405)

    try:
        data = json.loads(request.body)
        mode = (data.get('mode') or 'UPGRADE').upper()  # UPGRADE | ASSEMBLY | REPAIR
        main_item_id = data.get('main_item_id')
        technician = (data.get('technician') or '').strip()
        acc_code = str(data.get('acc_code') or '').strip()
        labor_charges = Decimal(str(data.get('labor_charges') or 0))
        additional_expense_desc = (data.get('additional_expense_desc') or 'Additional Expense').strip()
        additional_expense_amount = Decimal(str(data.get('additional_expense_amount') or 0))

        parts_in = data.get('parts_in', [])
        parts_out = data.get('parts_out', [])
        update_specs = data.get('update_specs') or {}

        if not main_item_id:
            return JsonResponse({'success': False, 'message': 'Main product is required.'})

        user_profile = getattr(request.user, 'userprofile', None)
        company = getattr(user_profile, 'company', None)
        branch = getattr(user_profile, 'branch', None)

        if not company or not branch:
            return JsonResponse({'success': False, 'message': 'Company/Branch not identified.'})

        main_item = Inventory.objects.filter(inv_id=main_item_id, company=company).first()
        if not main_item:
            return JsonResponse({'success': False, 'message': f'Main item (ID: {main_item_id}) not found.'})

        current_date = timezone.now().date()
        voucher_no = get_next_voucher('SADJ')
        upgrade_prefix = 'ASM' if mode == 'ASSEMBLY' else ('REP' if mode == 'REPAIR' else 'UPG')
        upgrade_no = f"{upgrade_prefix}-{voucher_no}"

        if not acc_code:
            acc_code = str(get_default_account_code('default_cash_acc', company.id, branch.id) or 110000001)
        acc_code_int = int(acc_code) if acc_code and acc_code.isdigit() else None

        total_parts_in_cost = Decimal('0')

        # 1. Process Parts IN (Components added/consumed)
        for part in parts_in:
            part_id = part.get('item_id')
            qty = Decimal(str(part.get('qty') or 1))
            if not part_id or qty <= 0:
                continue

            part_item = Inventory.objects.filter(inv_id=part_id, company=company).first()
            if not part_item:
                continue

            # Stock out part from inventory
            total_cogs, per_unit_cogs = STOCK_OUT(
                company_id=company.id,
                branch_id=branch.id,
                inventory_item_id=part_id,
                base_quantity_required=qty,
                voucher_date=current_date,
                voucher_type='ADJUSTMENT',
                voucher_bill_no=voucher_no,
                voucher_row_id=None,
                adj_type='ITEM_MAINTENANCE',
                acc_code=acc_code,
            )

            # Link StockLedger to this upgrade and main item with acc_code
            StockLedger.objects.filter(
                company=company,
                branch=branch,
                voucher_type='ADJUSTMENT',
                voucher_bill_no=voucher_no,
                inventory_item_id=part_id,
                upgrade_no__isnull=True
            ).update(upgrade_no=upgrade_no, linked_item=main_item, acc_code=acc_code_int)

            part_unit_cost = Decimal(str(part.get('cost') or per_unit_cogs or part_item.cost or 0))
            part_total_cost = part_unit_cost * qty
            total_parts_in_cost += part_total_cost

        # 2. Process Parts OUT (Components removed from device)
        for part_out in parts_out:
            part_id = part_out.get('item_id')
            qty = Decimal(str(part_out.get('qty') or 1))
            action = part_out.get('action') or 'RETURN_TO_STOCK'  # RETURN_TO_STOCK | SCRAP | RETURN_TO_CUSTOMER
            if qty <= 0:
                continue

            part_out_item = Inventory.objects.filter(inv_id=part_id, company=company).first() if part_id else None

            if action == 'RETURN_TO_STOCK' and part_out_item:
                unit_cost = Decimal(str(part_out.get('cost') or part_out_item.cost or 0))
                STOCK_IN(
                    company_id=company.id,
                    branch_id=branch.id,
                    inventory_item_id=part_out_item.inv_id,
                    base_quantity=qty,
                    rate_cost_per_unit=unit_cost,
                    voucher_date=current_date,
                    voucher_type='ADJUSTMENT',
                    voucher_bill_no=voucher_no,
                    voucher_row_id=None,
                    adj_type='ITEM_MAINTENANCE',
                    acc_code=acc_code,
                )
                StockLedger.objects.filter(
                    company=company,
                    branch=branch,
                    voucher_type='ADJUSTMENT',
                    voucher_bill_no=voucher_no,
                    inventory_item_id=part_out_item.inv_id,
                    upgrade_no__isnull=True
                ).update(upgrade_no=upgrade_no, linked_item=main_item, acc_code=acc_code_int)

        # 3. Handle Assembly Mode vs Upgrade/Repair Mode
        if mode == 'ASSEMBLY':
            # Finished product is stocked in
            total_assembly_cost = total_parts_in_cost + labor_charges + additional_expense_amount
            STOCK_IN(
                company_id=company.id,
                branch_id=branch.id,
                inventory_item_id=main_item.inv_id,
                base_quantity=Decimal('1'),
                rate_cost_per_unit=total_assembly_cost,
                voucher_date=current_date,
                voucher_type='ADJUSTMENT',
                voucher_bill_no=voucher_no,
                voucher_row_id=None,
                adj_type='ITEM_MAINTENANCE',
                acc_code=acc_code,
            )
            StockLedger.objects.filter(
                company=company,
                branch=branch,
                voucher_type='ADJUSTMENT',
                voucher_bill_no=voucher_no,
                inventory_item_id=main_item.inv_id,
                upgrade_no__isnull=True
            ).update(upgrade_no=upgrade_no, acc_code=acc_code_int)

            main_item.cost = total_assembly_cost
            main_item.last_pur_price = total_assembly_cost
            main_item.individual_cost = total_assembly_cost
            main_item.save(update_fields=['cost', 'last_pur_price', 'individual_cost'])
        else:
            # Upgrade / Repair: accumulate extra_cost on main_item
            added_extra = total_parts_in_cost + labor_charges + additional_expense_amount
            current_extra = Decimal(str(main_item.extra_cost or 0))
            main_item.extra_cost = current_extra + added_extra

            # Update specs if provided (e.g. upgraded RAM or Storage)
            update_fields = ['extra_cost']
            if update_specs.get('ram'):
                main_item.ram = update_specs['ram'].strip()
                update_fields.append('ram')
            if update_specs.get('storage'):
                main_item.storage = update_specs['storage'].strip()
                update_fields.append('storage')
            if update_specs.get('processor'):
                main_item.processor = update_specs['processor'].strip()
                update_fields.append('processor')
            if update_specs.get('condition'):
                main_item.condition = update_specs['condition'].strip()
                update_fields.append('condition')

            main_item.save(update_fields=update_fields)

        # 4. Create GLEDG Voucher CP (Cash Payment) for Labor / Service & Additional Charges
        paid_amount = labor_charges + additional_expense_amount
        if paid_amount > Decimal('0'):
            try:
                default_cash = get_default_account_code('default_cash_acc', company.id, branch.id) or 110000001
                counter_acc = acc_code_int if acc_code_int else int(default_cash)

                remarks_text = f"Upgrade #{upgrade_no} - {main_item.prod_name}"
                if technician and False:
                    remarks_text += f" (Tech: {technician})"

                lines = [
                    GledgLineDTO(
                        accCode=counter_acc,
                        head='',
                        notes=remarks_text,
                        receiptNo=0,
                        chqNo='0',
                        amount=paid_amount.quantize(Decimal('0.000')),
                        refAccCode=int(default_cash),
                        amtType="DR",
                    )
                ]

                created, msg, _vno = create_gledg_entries(
                    request=request,
                    lines=lines,
                    date=current_date,
                    v_type='CP',
                    remarks='',
                    pur_inv='M', # maintanance
                    inv_id=voucher_no,
                    called_by_invoices=True,
                )
                if not created:
                    print(f"[ItemUpgradation] Gledg creation warning for #{upgrade_no}: {msg}")
            except Exception as gledg_err:
                print(f"[ItemUpgradation] Gledg voucher creation error: {gledg_err}")

        bought = float(main_item.individual_cost or main_item.cost or 0)
        extra = float(main_item.extra_cost or 0)
        new_final = bought + extra

        return JsonResponse({
            'success': True,
            'message': f'{mode.capitalize()} saved successfully with Voucher #{upgrade_no}!',
            'voucher_no': voucher_no,
            'upgrade_no': upgrade_no,
            'new_final_cost': new_final,
            'total_extra_cost': extra,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
