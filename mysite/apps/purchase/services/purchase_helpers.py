
from decimal import Decimal
from apps.purchase.models import Purchase
from datetime import datetime
from apps.purchase.services.purchase_calculations import calculate_purchase_row

def now_karachi():
    from apps.myglobal.services.helpers import DateTimeHelper
    return DateTimeHelper().get_server_time()

def json_to_invoice(item=None, header_fields=None, fields_will_update=None, system_fields=None, is_header=False, update=False, landed_calc=None):
    item = item or {}
    header_fields = header_fields or {}
    fields_will_update = fields_will_update or {}
    system_fields = system_fields or {}
    
    # Use pre-calculated landed cost, don't recalculate
    row_data = landed_calc or calculate_purchase_row(item)

    # print('rowdata',row_data)
    
    invoice_data = {
        "bill_no": fields_will_update.get("bill_no"),
        "is_header": is_header,
        "dateent": fields_will_update.get("dateent"),
        "date": fields_will_update.get("date"),
        "dateedit": now_karachi() if update else None,
        "user": fields_will_update.get("user", ""),
        "edit_by": system_fields.get("user", "") if update else None,
        "header_edit_count": fields_will_update.get("header_edit_count", 0) if update else 0,
        "company": system_fields.get("company"),
        "branch": system_fields.get("branch"),
        "posterminal": system_fields.get("posterminal"),

        "inv_id": item.get("inv_id"),
        "prod_name": item.get("prod_name", ""),
        "category": item.get("category", ""),
        "qty": row_data["qty"],
        "foc_qty": row_data["foc_qty"],
        "rate": row_data["rate"],
        "packing_mode": item.get("packing_mode", 1),
        "uom": item.get('uom', None),
        "pack_qty": row_data["pack_qty"],

        "row_discount_percent": row_data["row_discount_percent"],
        "row_discount_amount": row_data["row_discount_amount"],
        "row_discount_percent2": row_data["row_discount_percent2"],
        "row_discount_amount2": row_data["row_discount_amount2"],
        "row_net_total": row_data["row_net_total"],
        
        # THIS IS YOUR REAL COST - PROFESSIONAL
        "row_total_cost_per_base_unit": row_data.get("row_total_cost", Decimal('0')),

        # "row_bonus": row_data["bonus"],
        "row_bonus_amount": item.get("row_bonus_amount", 0),

        "row_notes": item.get("row_notes", ""),
        "row_batch_no": item.get("row_batch_no", ""),
        "row_expiry_dt": datetime.strptime(item.get("row_expiry_dt"), '%Y-%m-%d').date() if item.get('row_expiry_dt') else None,
        "row_trade_price": item.get("row_trade_price", 0),
        "row_actual_retail_price": item.get("row_actual_retail_price", 0),
    }

    if is_header:
        invoice_data.update(header_fields)

    return Purchase(**invoice_data)
    
from apps.inventory.models import Inventory


# handles how cost is decided on pos sale or purchase time 
def handle_inventory_valuation(inv_id,qty,landed=0, called_from = 'PUR',old_base_qty= 0,update=False):
    # print('installing inventory',inv_id,qty,landed)
    if not inv_id:
        return False
    inv_val_method = 'normal'
    inv_method_list = ['normal','advance']
    print('qty in valuation',qty)
    
    if inv_val_method in inv_method_list:
        if inv_val_method == 'normal':
            try:
                inventory = Inventory.objects.select_for_update().get(inv_id=inv_id)
                if old_base_qty and update:
                    inventory.bal_qty += old_base_qty if called_from =='INV' else -old_base_qty

                inventory.bal_qty += qty if called_from == 'PUR' else -qty 

                if called_from == 'PUR':
                    inventory.last_pur_price = landed
                inventory.save()
                return True
            except Inventory.DoesNotExist:
                return True
            
        elif inv_val_method == 'advance':
            pass    
            
        