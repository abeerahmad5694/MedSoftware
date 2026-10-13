"""
inventory/services/valuation.py
================================
Production-ready O(N) inventory valuation engine.

Public API
----------
STOCK_IN(...)   - Call on Purchase save / Adjustment-In / Opening
STOCK_OUT(...) - Call on Invoice save to compute COGS and deduct stock

Both functions wrap a full atomic transaction and handle the
is_update=True reverse-then-reapply flow internally.

Valuation methods (read from CompanyConfiguration.config_data['general']['stock_valuation_method']):
  FIFO           - oldest lot first by receipt_date, id
  FEFO           - nearest expiry first, then receipt_date, id
  LIFO           - newest lot first by -receipt_date, -id
  AVERAGE        - qty allocation follows FIFO order; COGS = weighted avg of all available lots
  LAST_PUR_PRICE - COGS = Inventory.last_pur_price; still deducts lots FIFO for tracking
                   and updates Inventory.last_pur_price on receive.

StockLot field names (models.py):
  inventory_item   -> FK to Inventory  (inventory_item_id in queries)
  quantity_received
  quantity_remaining
  rate_cost_per_unit
  source_voucher_type
  source_bill_no
  source_row_id

StockLedger field names (models.py):
  inventory_item   -> FK to Inventory  (inventory_item_id in queries)
  stock_lot        -> FK to StockLot   (stock_lot_id in queries)
  base_quantity    -> + for IN, - for OUT
  rate_cost_per_unit
  net_value        -> base_quantity * rate_cost_per_unit
  voucher_type
  voucher_bill_no
  voucher_row_id
  voucher_date
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Tuple

from django.db import transaction
from django.db.models import F, Sum

from apps.inventory.models import Inventory, StockLot, StockLedger
from apps.configuration.models import CompanyConfiguration



# ─── Constants ─────────────────────────────────────────────────────────────────
VALUATION_METHODS = ('FIFO', 'FEFO', 'LIFO', 'AVERAGE', 'LAST_PUR_PRICE')
DEFAULT_METHOD = 'LAST_PUR_PRICE'
STRICT_MODE = True



# ─── Configuration helper ───────────────────────────────────────────────────────
def _get_valuation_method(company_id: int, branch_id: int) -> str:
    """
    Read stock_valuation_method from CompanyConfiguration.config_data['general'].
    Falls back to DEFAULT_METHOD if not configured.
    """
    try:
        method = CompanyConfiguration.objects.only('stock_valuation_method').get(
            company_id=company_id, branch_id=branch_id
        ).stock_valuation_method or DEFAULT_METHOD
        # method = cfg.get_setting('general', 'stock_valuation_method', DEFAULT_METHOD)
        # method = cfg.get('stock_valuation_method', DEFAULT_METHOD)
        return method if method in VALUATION_METHODS else DEFAULT_METHOD
    except CompanyConfiguration.DoesNotExist:
        return DEFAULT_METHOD


def _get_inventory_item(company_id: int, branch_id: int, inventory_item_id: int) -> Inventory:
    return Inventory.objects.select_for_update().get(
        inv_id=inventory_item_id,
        company_id=company_id,
        branch_id=branch_id,
    )


def _order_lots_for_method(lots_qs, method: str):
    """Apply the correct ordering to a StockLot queryset based on valuation method."""
    if method == 'FEFO':
        return lots_qs.order_by(F('expiry_date').asc(nulls_last=True), 'receipt_date', 'id')
    elif method == 'LIFO':
        return lots_qs.order_by('-receipt_date', '-id')
    else:
        # FIFO, AVERAGE, LAST_PUR_PRICE all deduct oldest-first for qty tracking
        return lots_qs.order_by('receipt_date', 'id')

def _reverse_voucher_stock(company_id, branch_id, voucher_type, voucher_bill_no, block_if_partially_sold=True):
    ledger_entries = StockLedger.objects.select_for_update().filter(
        company_id=company_id, branch_id=branch_id,
        voucher_type=voucher_type, voucher_bill_no=voucher_bill_no,
    )
    if not ledger_entries.exists():
        return

    if voucher_type == 'PURCHASE':
        lot_ids = list(ledger_entries.exclude(stock_lot_id=None).values_list('stock_lot_id', flat=True).distinct())
        if lot_ids and block_if_partially_sold and STRICT_MODE:
            bad = StockLot.objects.filter(id__in=lot_ids).exclude(quantity_remaining=F('quantity_received'))
            if bad.exists():
                raise ValueError(f"Cannot edit PURCHASE {voucher_bill_no} - already sold.")
        for inv_id in ledger_entries.values_list('inventory_item_id', flat=True).distinct():
            total_qty = ledger_entries.filter(inventory_item_id=inv_id).aggregate(s=Sum('base_quantity'))['s'] or 0
            Inventory.objects.filter(inv_id=inv_id).update(bal_qty=F('bal_qty') - total_qty)
        ledger_entries.delete()
        StockLot.objects.filter(id__in=lot_ids).delete()
        return

    # SALE, SALE_RETURN, PURCHASE_RETURN, ADJUSTMENT -> ONE time restore only
    for led in ledger_entries.select_related('stock_lot'):
        if led.stock_lot_id:
            StockLot.objects.filter(id=led.stock_lot_id).update(
                quantity_remaining=F('quantity_remaining') - led.base_quantity
            )
    for inv_id in ledger_entries.values_list('inventory_item_id', flat=True).distinct():
        total_qty = ledger_entries.filter(inventory_item_id=inv_id).aggregate(s=Sum('base_quantity'))['s'] or 0
        Inventory.objects.filter(inv_id=inv_id).update(bal_qty=F('bal_qty') - total_qty)
    
    ledger_entries.delete()

# def _reverse_voucher_stock(company_id, branch_id, voucher_type, voucher_bill_no, block_if_partially_sold=True):
#     ledger_entries = StockLedger.objects.select_for_update().filter(
#         company_id=company_id, branch_id=branch_id,
#         voucher_type=voucher_type,
#         voucher_bill_no=voucher_bill_no,
#     )

#     if not ledger_entries.exists():
#         return

#     # 1. For SALE - put qty back to lots
#     if voucher_type in ('SALE', 'ADJUSTMENT', 'SALE_RETURN', 'PURCHASE_RETURN'):
#         for led in ledger_entries.select_related('stock_lot'):
#             if led.stock_lot_id:
#                 StockLot.objects.filter(id=led.stock_lot_id).update(
#                     quantity_remaining=F('quantity_remaining') - led.base_quantity
#                 )
#                 Inventory.objects.filter(inv_id=led.inventory_item_id).update(
#                     bal_qty=F('bal_qty') - led.base_quantity
#                 )

#     # 2. For PURCHASE - if lot not sold, DELETE lot completely, don't keep zero lots
#     elif voucher_type == 'PURCHASE':
#         lot_ids = list(ledger_entries.exclude(stock_lot_id=None).values_list('stock_lot_id', flat=True).distinct())
#         if lot_ids:
#             # Check if any lot partially sold
#             if block_if_partially_sold and STRICT_MODE:
#                 bad = StockLot.objects.filter(id__in=lot_ids).exclude(quantity_remaining=F('quantity_received'))
#                 if bad.exists():
#                     raise ValueError(f"Cannot perfome this action. PURCHASE {voucher_bill_no} - already sold. Contact Administration")

#             # Delete ledger first
#             for inv_id in ledger_entries.values_list('inventory_item_id', flat=True).distinct():
#                 total_qty = ledger_entries.filter(inventory_item_id=inv_id).aggregate(s=Sum('base_quantity'))['s'] or 0
#                 Inventory.objects.filter(inv_id=inv_id).update(bal_qty=F('bal_qty') - total_qty)

#             ledger_entries.delete()
#             # NOW delete the lots - this is the missing part
#             StockLot.objects.filter(id__in=lot_ids).delete()
#             return

#     # For SALE, delete ledger after restore
#     # For PURCHASE we already deleted
#     if voucher_type!= 'PURCHASE':
#         # adjust bal_qty already done above for SALE
#         # for SALE we already restored, just delete ledger
#         if voucher_type in ('SALE',):
#             ledger_entries.delete()
#         else:
#             # generic
#             for inv_id in ledger_entries.values_list('inventory_item_id', flat=True).distinct():
#                 total_qty = ledger_entries.filter(inventory_item_id=inv_id).aggregate(s=Sum('base_quantity'))['s'] or 0
#                 Inventory.objects.filter(inv_id=inv_id).update(bal_qty=F('bal_qty') - total_qty)
#             ledger_entries.delete()
            
            
            
            
# # ─── Reverse helper ─────────────────────────────────────────────────────────────
# def _reverse_voucher_stock(
#     company_id: int,
#     branch_id: int,
#     voucher_type: str,
#     voucher_bill_no: int,
#     block_if_partially_sold: bool = True,
# ) -> None:
#     """
#     Reverse all StockLedger entries for a given voucher.
#     Restores StockLot.quantity_remaining and Inventory.bal_qty.
#     Must be called inside an atomic block.

#     Raises ValueError if a PURCHASE lot has already been partially sold
#     (quantity_remaining < quantity_received).
#     """
#     ledger_entries = StockLedger.objects.select_for_update().filter(
#         company_id=company_id,
#         branch_id=branch_id,
#         voucher_type=voucher_type,
#         voucher_bill_no=voucher_bill_no,
#     ).select_related('stock_lot')

#     if not ledger_entries.exists():
#         return  # Nothing to reverse (first-time save, no prior stock entry)

#     # Group by item and lot to do O(N) updates
#     # Structure: {inv_id: {lot_id: signed_qty_to_restore}}
#     item_lot_restore: dict[int, dict[int | None, Decimal]] = {}
#     item_qty_restore: dict[int, Decimal] = {}  # net qty change to restore on Inventory.bal_qty

#     for ledger_row in ledger_entries:
#         inv_id = ledger_row.inventory_item_id
#         lot_id = ledger_row.stock_lot_id
#         qty_in_ledger = ledger_row.base_quantity  # positive = receive, negative = issue

#         item_qty_restore.setdefault(inv_id, Decimal(0))
#         item_qty_restore[inv_id] -= qty_in_ledger  # reverse the direction

#         if lot_id is not None:
#             item_lot_restore.setdefault(inv_id, {}).setdefault(lot_id, Decimal(0))
#             item_lot_restore[inv_id][lot_id] -= qty_in_ledger

#     # Validate: for PURCHASE reverse, ensure none of the lots are partially sold
#     if block_if_partially_sold and voucher_type == 'PURCHASE':
#         all_lot_ids = [lid for lots in item_lot_restore.values() for lid in lots]
#         if all_lot_ids:
#             problem_lots = StockLot.objects.filter(
#                 id__in=all_lot_ids
#             ).exclude(quantity_remaining=F('quantity_received'))
#             if problem_lots.exists():
#                 sold_items = ', '.join(str(l.inventory_item_id) for l in problem_lots[:5])
#                 raise ValueError(
#                     f"Cannot edit purchase. Stock for items [{sold_items}] has already been partially sold. "
#                     "Create a Purchase Return instead."
#                 )

#     # Restore lot quantity_remaining using F() — no per-item DB round-trip
#     for inv_id, lots in item_lot_restore.items():
#         for lot_id, qty_to_restore in lots.items():
#             StockLot.objects.filter(id=lot_id).update(
#                 quantity_remaining=F('quantity_remaining') + qty_to_restore
#             )

#     # Restore Inventory.bal_qty using F()
#     for inv_id, qty_to_restore in item_qty_restore.items():
#         Inventory.objects.filter(inv_id=inv_id).update(
#             bal_qty=F('bal_qty') + qty_to_restore
#         )

#     # Delete the ledger entries
#     ledger_entries.delete()


# ─── STOCK_IN ─────────────────────────────────────────────────────────────
@transaction.atomic
def STOCK_IN(
    company_id: int,
    branch_id: int,
    inventory_item_id: int,
    base_quantity: Decimal,
    rate_cost_per_unit: Decimal,
    voucher_date,
    voucher_type: str,
    voucher_bill_no: int,
    voucher_row_id: int | None = None,
    expiry_date=None,
    is_update: bool = False,
    adj_type: str = None,
    acc_code: str = None,
    batch_no: str = None,
) -> StockLot:
    """
    Record stock IN (purchase, opening, adjustment-in) or PURCHASE RETURN (if qty < 0).

    Parameters
    ----------
    base_quantity       : qty in base units (qty * pack_qty for purchase rows)
    rate_cost_per_unit  : Purchase.row_total_cost_per_base_unit
    voucher_date        : Purchase.date
    voucher_type        : 'PURCHASE' | 'OPENING' | 'ADJUSTMENT'
    voucher_bill_no     : Purchase.bill_no
    voucher_row_id      : Purchase.id (PK of the row)
    expiry_date         : Purchase.row_expiry_dt
    is_update           : If True, reverses existing ledger for this voucher first.

    Returns the created StockLot.
    """
    base_quantity = Decimal(str(base_quantity))
    rate_cost_per_unit = Decimal(str(rate_cost_per_unit))

    if is_update:
        _reverse_voucher_stock(
            company_id, branch_id, voucher_type, voucher_bill_no,
            block_if_partially_sold=(voucher_type == 'PURCHASE'),
        )

    if base_quantity < 0:
        # PURCHASE RETURN
        return_qty = abs(base_quantity)
        lots_to_deduct = None
        
        # 1. Match by batch_no
        if batch_no:
            lots_to_deduct = list(StockLot.objects.select_for_update().filter(
                company_id=company_id, branch_id=branch_id, inventory_item_id=inventory_item_id,
                batch_no=batch_no, quantity_remaining__gt=0
            ).order_by('receipt_date', 'id'))
            
        # 2. If no batch_no or not found, match by expiry_date
        if not lots_to_deduct and expiry_date:
            lots_to_deduct = list(StockLot.objects.select_for_update().filter(
                company_id=company_id, branch_id=branch_id, inventory_item_id=inventory_item_id,
                expiry_date=expiry_date, quantity_remaining__gt=0
            ).order_by('receipt_date', 'id'))
            
        # 3. If still not found, FIFO
        if not lots_to_deduct:
            lots_to_deduct = list(StockLot.objects.select_for_update().filter(
                company_id=company_id, branch_id=branch_id, inventory_item_id=inventory_item_id,
                quantity_remaining__gt=0
            ).order_by('receipt_date', 'id'))

        remaining_to_deduct = return_qty
        ledger_rows_to_create = []
        lots_to_update = []
        
        for lot in lots_to_deduct:
            if remaining_to_deduct <= 0:
                break
            allocated = min(lot.quantity_remaining, remaining_to_deduct)
            
            ledger_rows_to_create.append(StockLedger(
                company_id=company_id,
                branch_id=branch_id,
                inventory_item_id=inventory_item_id,
                stock_lot=lot,
                base_quantity=-allocated,  # negative for OUT (purchase return)
                rate_cost_per_unit=lot.rate_cost_per_unit,
                net_value=-(allocated * lot.rate_cost_per_unit),
                voucher_type=voucher_type,
                voucher_bill_no=voucher_bill_no,
                voucher_row_id=voucher_row_id,
                voucher_date=voucher_date,
                adj_type=adj_type,
                acc_code=acc_code,
                batch_no=batch_no,
            ))
            lots_to_update.append((lot.id, lot.quantity_remaining - allocated))
            remaining_to_deduct -= allocated
            
        if remaining_to_deduct > 0:
            # Fallback
            ledger_rows_to_create.append(StockLedger(
                company_id=company_id,
                branch_id=branch_id,
                inventory_item_id=inventory_item_id,
                stock_lot=None,
                base_quantity=-remaining_to_deduct,
                rate_cost_per_unit=rate_cost_per_unit,
                net_value=-(remaining_to_deduct * rate_cost_per_unit),
                voucher_type=voucher_type,
                voucher_bill_no=voucher_bill_no,
                voucher_row_id=voucher_row_id,
                voucher_date=voucher_date,
                adj_type=adj_type,
                acc_code=acc_code,
                batch_no=batch_no,
            ))
            
        if ledger_rows_to_create:
            StockLedger.objects.bulk_create(ledger_rows_to_create)
        for lot_id, new_qty in lots_to_update:
            StockLot.objects.filter(id=lot_id).update(quantity_remaining=new_qty)
            
        Inventory.objects.filter(
            inv_id=inventory_item_id, company_id=company_id, branch_id=branch_id
        ).update(bal_qty=F('bal_qty') - return_qty)
        
        return None

    # Create the new lot
    new_lot = StockLot.objects.create(
        company_id=company_id,
        branch_id=branch_id,
        inventory_item_id=inventory_item_id,
        quantity_received=base_quantity,
        quantity_remaining=base_quantity,
        rate_cost_per_unit=rate_cost_per_unit,
        expiry_date=expiry_date,
        batch_no=batch_no,
        receipt_date=voucher_date,
        source_voucher_type=voucher_type,
        source_bill_no=voucher_bill_no,
        source_row_id=voucher_row_id,
        acc_code = acc_code,
    )

    # Write to ledger
    StockLedger.objects.create(
        company_id=company_id,
        branch_id=branch_id,
        inventory_item_id=inventory_item_id,
        stock_lot=new_lot,
        base_quantity=base_quantity,
        rate_cost_per_unit=rate_cost_per_unit,
        net_value=base_quantity * rate_cost_per_unit,
        voucher_type=voucher_type,
        voucher_bill_no=voucher_bill_no,
        voucher_row_id=voucher_row_id,
        voucher_date=voucher_date,
        acc_code = acc_code,
        adj_type=adj_type,
        batch_no=batch_no,
    )

    # Update Inventory.bal_qty and last_pur_price (for PURCHASE / LAST_PUR_PRICE)
    method = _get_valuation_method(company_id, branch_id)
    update_kwargs: dict = {'bal_qty': F('bal_qty') + base_quantity}
    if voucher_type == 'PURCHASE' or method == 'LAST_PUR_PRICE':
        update_kwargs['last_pur_price'] = rate_cost_per_unit

    Inventory.objects.filter(
        inv_id=inventory_item_id,
        company_id=company_id,
        branch_id=branch_id,
    ).update(**update_kwargs)

    return new_lot


# ─── STOCK_OUT ──────────────────────────────────────────────────────────
@transaction.atomic
def STOCK_OUT(
    company_id: int,
    branch_id: int,
    inventory_item_id: int,
    base_quantity_required: Decimal,
    voucher_date,
    voucher_type: str,
    voucher_bill_no: int,
    voucher_row_id: int | None = None,
    is_update: bool = False,
    adj_type: str = None,
    acc_code: str = None,
    batch_no: str = None,
) -> Tuple[Decimal, Decimal]:
    """
    Deduct stock and return (total_cogs, per_unit_cogs).
    Handles SALE RETURN (if qty < 0) to put stock back.

    Save the returned values into Invoice.row_net_cost and Invoice.row_rate_cost.

    Parameters
    ----------
    base_quantity_required : qty in base units (qty * pack_qty)
    voucher_type           : 'SALE' | 'ADJUSTMENT' | 'SALE_RETURN' (negative for return)
    is_update              : If True, reverses existing ledger for this voucher_bill_no first.

    Returns
    -------
    (total_cogs, per_unit_cogs)
    """
    base_quantity_required = Decimal(str(base_quantity_required))

    if is_update:
        _reverse_voucher_stock(
            company_id, branch_id, voucher_type, voucher_bill_no,
            block_if_partially_sold=False,
        )

    if base_quantity_required < 0:
        # SALE RETURN
        return_qty = abs(base_quantity_required)
        
        # User: "when qty is < 0 then quantiny remaining must be plus"
        # Find the latest lot to add the returned quantity back to
        # latest_lot = StockLot.objects.select_for_update().filter(
        #     company_id=company_id,
        #     branch_id=branch_id,
        #     inventory_item_id=inventory_item_id
        # ).order_by('-receipt_date', '-id').first()
        
        
        latest_lot = None
        if batch_no:
            latest_lot = StockLot.objects.select_for_update().filter(
                company_id=company_id, branch_id=branch_id,
                inventory_item_id=inventory_item_id,
                batch_no=batch_no
            ).order_by('-receipt_date', '-id').first()
        
        if not latest_lot:
            latest_lot = StockLot.objects.select_for_update().filter(
                company_id=company_id, branch_id=branch_id,
                inventory_item_id=inventory_item_id
            ).order_by('-receipt_date', '-id').first()
        
        
        
        
        
        inventory_item = _get_inventory_item(company_id, branch_id, inventory_item_id)
        per_unit_cogs = inventory_item.last_pur_price or inventory_item.cost or Decimal(0)
        
        
        
        
        
        if latest_lot:
            per_unit_cogs = latest_lot.rate_cost_per_unit
            StockLot.objects.filter(id=latest_lot.id).update(
                quantity_remaining=F('quantity_remaining') + return_qty
            )
            
            
            
            
            
        total_cogs = per_unit_cogs * base_quantity_required # negative total cogs
        
        StockLedger.objects.create(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            stock_lot=latest_lot,
            base_quantity=return_qty, # base_quantity_required is < 0, so return_qty is positive (stock IN)
            rate_cost_per_unit=per_unit_cogs,
            net_value=per_unit_cogs * return_qty,
            voucher_type=voucher_type,
            voucher_bill_no=voucher_bill_no,
            voucher_row_id=voucher_row_id,
            voucher_date=voucher_date,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=batch_no,
        )
        
        Inventory.objects.filter(inv_id=inventory_item_id, company_id=company_id, branch_id=branch_id).update(
            bal_qty=F('bal_qty') + return_qty
        )
        
        return total_cogs, per_unit_cogs

    method = _get_valuation_method(company_id, branch_id)

    # Handle LAST_PUR_PRICE: COGS from Inventory.last_pur_price, still deduct lots
    if method == 'LAST_PUR_PRICE':
        inventory_item = _get_inventory_item(company_id, branch_id, inventory_item_id)
        per_unit_cogs = inventory_item.last_pur_price or inventory_item.cost or Decimal(0)
        total_cogs = per_unit_cogs * base_quantity_required
        _deduct_lots_tracking_only(
            company_id, branch_id, inventory_item_id,
            base_quantity_required, voucher_date, voucher_type, voucher_bill_no, voucher_row_id,
            per_unit_cogs=per_unit_cogs,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=batch_no,
        )
        Inventory.objects.filter(inv_id=inventory_item_id, company_id=company_id, branch_id=branch_id).update(
            bal_qty=F('bal_qty') - base_quantity_required
        )
        return total_cogs, per_unit_cogs

    # For FIFO / FEFO / LIFO / AVERAGE: load lots once (O(N))
    available_lots = list(
        _order_lots_for_method(
            StockLot.objects.select_for_update().filter(
                company_id=company_id,
                branch_id=branch_id,
                inventory_item_id=inventory_item_id,
                quantity_remaining__gt=0,
                
            ),
            method,
        )
    )

    if method == 'AVERAGE':
        # Compute weighted average across ALL available lots
        total_value = sum(lot.quantity_remaining * lot.rate_cost_per_unit for lot in available_lots)
        total_qty_available = sum(lot.quantity_remaining for lot in available_lots)
        per_unit_cogs = (total_value / total_qty_available) if total_qty_available > 0 else Decimal(0)
    else:
        per_unit_cogs = Decimal(0)  # computed per-lot below for FIFO/FEFO/LIFO

    remaining_to_allocate = base_quantity_required
    total_cogs = Decimal(0)
    ledger_rows_to_create: List[StockLedger] = []
    lots_to_update: List[Tuple[int, Decimal]] = []  # (lot_id, new_quantity_remaining)

    for lot in available_lots:
        if remaining_to_allocate <= 0:
            break

        allocated_from_this_lot = min(lot.quantity_remaining, remaining_to_allocate)
        new_remaining = lot.quantity_remaining - allocated_from_this_lot

        if method == 'AVERAGE':
            cost_for_allocation = allocated_from_this_lot * per_unit_cogs
        else:
            cost_for_allocation = allocated_from_this_lot * lot.rate_cost_per_unit
            per_unit_cogs = lot.rate_cost_per_unit  # last used lot's cost for simple per_unit

        total_cogs += cost_for_allocation
        remaining_to_allocate -= allocated_from_this_lot

        ledger_rows_to_create.append(StockLedger(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            stock_lot=lot,
            base_quantity=-allocated_from_this_lot,  # negative = issue
            rate_cost_per_unit=lot.rate_cost_per_unit if method != 'AVERAGE' else per_unit_cogs,
            net_value=-cost_for_allocation,
            voucher_type=voucher_type,
            voucher_bill_no=voucher_bill_no,
            voucher_row_id=voucher_row_id,
            voucher_date=voucher_date,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=lot.batch_no,
        ))
        lots_to_update.append((lot.id, new_remaining))

    # Handle shortfall (insufficient lots): use last_pur_price as fallback
    if remaining_to_allocate > 0:
        inventory_item = _get_inventory_item(company_id, branch_id, inventory_item_id)
        fallback_cost = inventory_item.last_pur_price or inventory_item.cost or Decimal(0)
        fallback_total = remaining_to_allocate * fallback_cost
        total_cogs += fallback_total
        per_unit_cogs = fallback_cost

        ledger_rows_to_create.append(StockLedger(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            stock_lot=None,
            base_quantity=-remaining_to_allocate,
            rate_cost_per_unit=fallback_cost,
            net_value=-fallback_total,
            voucher_type=voucher_type,
            voucher_bill_no=voucher_bill_no,
            voucher_row_id=voucher_row_id,
            voucher_date=voucher_date,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=batch_no,
        ))

    # Bulk write ledger (one query)
    if ledger_rows_to_create:
        StockLedger.objects.bulk_create(ledger_rows_to_create)

    # Update lot quantity_remaining using individual F() updates (unavoidable O(N_lots), but no SELECT)
    for lot_id, new_quantity_remaining in lots_to_update:
        StockLot.objects.filter(id=lot_id).update(quantity_remaining=new_quantity_remaining)

    # Update Inventory.bal_qty in one query
    Inventory.objects.filter(
        inv_id=inventory_item_id, company_id=company_id, branch_id=branch_id
    ).update(bal_qty=F('bal_qty') - base_quantity_required)

    # For FIFO/FEFO/LIFO: compute true per_unit from totals
    if method != 'AVERAGE':
        total_allocated = base_quantity_required
        per_unit_cogs = (total_cogs / total_allocated) if total_allocated > 0 else Decimal(0)

    return total_cogs, per_unit_cogs


def _deduct_lots_tracking_only(
    company_id: int,
    branch_id: int,
    inventory_item_id: int,
    base_quantity: Decimal,
    voucher_date,
    voucher_type: str,
    voucher_bill_no: int,
    voucher_row_id: int | None,
    per_unit_cogs: Decimal,
    adj_type: str = None,
    acc_code: str = None,
    batch_no: str = None,
) -> None:
    """
    LAST_PUR_PRICE mode: deduct lots FIFO for qty tracking but use fixed per_unit_cogs for value.
    """
    available_lots = list(
        StockLot.objects.select_for_update().filter(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            quantity_remaining__gt=0,
        ).order_by('receipt_date', 'id')
    )

    remaining = base_quantity
    ledger_rows: List[StockLedger] = []
    lot_updates: List[Tuple[int, Decimal]] = []

    for lot in available_lots:
        if remaining <= 0:
            break
        allocated = min(lot.quantity_remaining, remaining)
        ledger_rows.append(StockLedger(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            stock_lot=lot,
            base_quantity=-allocated,
            rate_cost_per_unit=per_unit_cogs,
            net_value=-(allocated * per_unit_cogs),
            voucher_type=voucher_type,
            voucher_bill_no=voucher_bill_no,
            voucher_row_id=voucher_row_id,
            voucher_date=voucher_date,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=lot.batch_no,
        ))
        lot_updates.append((lot.id, lot.quantity_remaining - allocated))
        remaining -= allocated

    if remaining > 0:
        ledger_rows.append(StockLedger(
            company_id=company_id,
            branch_id=branch_id,
            inventory_item_id=inventory_item_id,
            stock_lot=None,
            base_quantity=-remaining,
            rate_cost_per_unit=per_unit_cogs,
            net_value=-(remaining * per_unit_cogs),
            voucher_type=voucher_type,
            voucher_bill_no=voucher_bill_no,
            voucher_row_id=voucher_row_id,
            voucher_date=voucher_date,
            adj_type=adj_type,
            acc_code=acc_code,
            batch_no=batch_no,
        ))

    if ledger_rows:
        StockLedger.objects.bulk_create(ledger_rows)
    for lot_id, new_qty in lot_updates:
        StockLot.objects.filter(id=lot_id).update(quantity_remaining=new_qty)


# ─── Legacy compatibility wrapper ──────────────────────────────────────────────
def get_item_valuation(item_id, qty, company_id, branch_id, method=None):
    """
    Backward-compatible wrapper for stock_adjustment.py.
    Returns (total_cost, avg_unit_cost, []).
    Does NOT write to StockLot/StockLedger — read-only estimate only.
    """
    try:
        qty = Decimal(str(qty))
    except Exception:
        qty = Decimal(0)

    if qty <= 0:
        return Decimal(0), Decimal(0), []

    try:
        item = Inventory.objects.get(inv_id=item_id, company_id=company_id, branch_id=branch_id)
    except Inventory.DoesNotExist:
        return Decimal(0), Decimal(0), []

    effective_method = method or _get_valuation_method(company_id, branch_id)

    if effective_method == 'LAST_PUR_PRICE':
        unit_cost = item.last_pur_price or item.cost or Decimal(0)
        return unit_cost * qty, unit_cost, []

    if effective_method == 'AVERAGE':
        agg = StockLot.objects.filter(
            company_id=company_id, branch_id=branch_id,
            inventory_item_id=item_id, quantity_remaining__gt=0
        ).aggregate(
            total_val=Sum(F('quantity_remaining') * F('rate_cost_per_unit')),
            total_qty=Sum('quantity_remaining')
        )
        total_qty = agg['total_qty'] or Decimal(0)
        if total_qty <= 0:
            unit_cost = item.cost or Decimal(0)
            return unit_cost * qty, unit_cost, []
        avg_cost = (agg['total_val'] or Decimal(0)) / total_qty
        return avg_cost * qty, avg_cost, []

    lots = list(
        _order_lots_for_method(
            StockLot.objects.filter(
                company_id=company_id, branch_id=branch_id,
                inventory_item_id=item_id, quantity_remaining__gt=0
            ),
            effective_method,
        )
    )
    remaining = qty
    total_cost = Decimal(0)
    for lot in lots:
        if remaining <= 0:
            break
        alloc = min(lot.quantity_remaining, remaining)
        total_cost += alloc * lot.rate_cost_per_unit
        remaining -= alloc

    if remaining > 0:
        fallback = item.last_pur_price or item.cost or Decimal(0)
        total_cost += remaining * fallback

    avg = total_cost / qty if qty > 0 else Decimal(0)
    return total_cost, avg, []
