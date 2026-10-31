# Implementation Plan: SERIAL Tracking in Purchase Cart

## 1. High-Level Architecture Overview
This plan implements end-to-end SERIAL item tracking in the Purchase workflow. Items marked with `tracking_type == 'SERIAL'` will be tracked with dynamic per-category serial specifications and per-piece individual costs. 

### Core Components:
1. **Frontend Cart State (`cart.js`)**:
   - Detect `tracking_type === 'SERIAL'` on product addition.
   - Maintain parent row with computed read-only `qty` (length of child serials), disabled rate `'-'`, and `amount` = sum of children costs.
   - Embed an inline nested table directly under the parent row without gaps (`width: 92%`, centered, `#f1f5f9` background, `#e2e8f0` border, `8px` radius).
   - Render dynamic columns based on category `serial_fields_config` (fallback to `"0"`), always showing editable `Cost`.
   - Provide `+ Add Serial` button and per-child `X` delete button. Live update parent `qty`, `amount`, and cart grand totals on changes.
2. **Payload Construction (`payload.js`)**:
   - Separate `items` (NONE tracking items only) and `serial_items` (child serial records containing `parent_inv_id`, `serial_no`, `serial_no2`, specs, `condition`, `warranty_end`, and `cost`).
   - Validate required serial numbers and in-cart duplicates prior to payload emission.
3. **Backend Processing (`apps/purchase/api/purchase_crud.py`)**:
   - Inside `transaction.atomic()`, validate serial numbers against existing active inventory (`bal_qty > 0`) in $O(N)$ with a single query.
   - Bulk-create child `Inventory` instances (`parent_item=parent`, `is_variant=True`, `tracking_type='SERIAL'`, `bal_qty=1`, `status='IN_STOCK'`, `individual_cost=cost`, specs).
   - Convert newly created child instances into standard `items` entries (`inv_id=child.inv_id`, `qty=1`, `rate=cost`, `batch_no=serial_no`).
   - Allow existing purchase saving loop (`calculate_landed_cost`, `StockLot`, `StockLedger`, `Gledg`) to execute seamlessly.

---

## 2. Detailed Technical Plan

### A. Frontend: `apps/purchase/static/purchase/js/cart.js`
- **Helper `getSerialFieldsConfigForCategory(catId)`**:
  - Reads `window.companyConfigurations?.inventory?.serial_fields_config`.
  - Resolves config for `catId` or `"0"`. Sorts fields by `sort_order`.
- **`addToLocalCart(products)`**:
  - If `product.tracking_type === 'SERIAL'`:
    - Check if parent already in cart (when `!multiline.checked`). If so, append a new serial child row.
    - Otherwise, create parent cart item with `is_serial: true`, `tracking_type: 'SERIAL'`, `serial_items: [ defaultSerialRow ]`, `qty: 1`, `rate: '-'`, `amount: defaultSerialRow.cost`.
- **`renderCart(cart)`**:
  - For `is_serial` items, render parent `<tr>` with disabled rate and readonly qty.
  - Immediately following parent `<tr>`, render nested serial table row `<tr class="serial-nested-row">` spanning all columns.
  - Table header displays dynamic columns (serial_no, specs, condition, warranty) + explicit `Cost*` column + action `▲`.
  - Sub-table rows display inputs: text inputs for specs, dropdown for condition, datepicker for warranty_end, number input for cost.
- **Event Handling**:
  - Delegated listener on `cartBody`:
    - `+ Add Serial`: Adds new serial row, updates parent `qty` and `amount`, updates UI.
    - `X` on serial row: Removes serial row, updates parent `qty` and `amount`. If no serials remain, removes parent row.
    - `change`/`input` on serial inputs: Updates in-memory child fields. For `cost`, immediately recalculates parent amount and footers.

### B. Payload Builder: `apps/purchase/static/purchase/js/payload.js`
- Separate items into:
  - `items`: Items where `tracking_type !== 'SERIAL'`.
  - `serial_items`: Extracted from all serial parents (`parent_inv_id`, `serial_no`, `serial_no2`, `color`, `processor`, `ram`, `storage`, `condition`, `model_year`, `warranty_end`, `cost`).
- Validate serial numbers: ensure non-empty for required serials, and ensure no duplicates within the cart.

### C. Backend: `apps/purchase/api/purchase_crud.py`
- Extract `serial_items = data.get("serial_items", [])`.
- If `serial_items`:
  1. $O(N)$ In-memory duplicate check in payload.
  2. $O(N)$ DB check: `Inventory.objects.filter(company=company, serial_no__in=serial_nos, bal_qty__gt=0).values_list('serial_no', flat=True)`. Return error if duplicate exists.
  3. Bulk fetch parent products in 1 query: `parents = Inventory.objects.in_bulk(parent_ids)`.
  4. Instantiate child `Inventory` models with `parent_item=parent`, `is_variant=True`, `tracking_type='SERIAL'`, `bal_qty=1`, `status='IN_STOCK'`, `individual_cost=cost`, `prod_name=f"{parent.prod_name} - {serial_no}"`.
  5. `Inventory.objects.bulk_create(new_children)`.
  6. Append generated child items to `items`:
     ```python
     items.append({
         'inv_id': child.inv_id,
         'prod_name': child.prod_name,
         'qty': 1,
         'rate': float(child.individual_cost or 0),
         'packing_mode': 1,
         'pack_qty': 1,
         'row_discount_percent': 0,
         'row_discount_amount': 0,
         'row_net_total': float(child.individual_cost or 0),
         'row_batch_no': child.serial_no or "",
         'row_expiry_dt': str(child.warranty_end) if child.warranty_end else None,
     })
     ```
- Existing purchase save loop processes the unified `items` list without changes.

---

## 3. Verification & Approval
- Lead_Architect Approval: APPROVED.
- Next Step: Code_Engineer implements with minimal diffs and verifies with django checks and end-to-end payload consistency.

