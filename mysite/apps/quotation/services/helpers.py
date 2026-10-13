from apps.sale.services.sale_calculations import calculate_row_totals, calculate_header_totals ,calculate_cost
from decimal import Decimal
from apps.sale.models import Invoice ,BarcodConfig
def now_karachi():
    from apps.myglobal.services.helpers import DateTimeHelper
    return DateTimeHelper().get_server_time()






def scan_barcode(request, code):
    # Ensure the user always has a BarcodConfig
    config, created = BarcodConfig.objects.get_or_create(
        user = 'main_bc',
        defaults={'price_base': 'N'}
    )
    # print(request.user)
    product = None
    weight_total = None

    try:
        # Fast exact match
        # product = Inventory.objects.filter(
        #     Q(barcode = str(code)) | Q(inv_id = int(code)) | Q(manualbc__iexact = str(code)) 
        # ).first()
        product = Inventory.objects.filter(manualbc__iexact=str(code)).first()

        if not product:
            
            product = Inventory.objects.filter(barcode=str(code)).first()
            
        if not product:
            

            product = Inventory.objects.filter(inv_id=int(code)).first()

        
            
        if product:
            

            return product, None
    except Exception as e:
        # Optional: log the exception
        print(f"Exact match error: {e}")

    # Weighted barcode
    if len(code) == config.total_bc_digits:
        
        try:
            trimmed = code[config.left_delete:len(code)-config.right_delete]
            item_code = trimmed[:config.item_bc]
            w = trimmed[config.item_bc:]
            kg = w[:config.kg]
            gr = w[config.kg:config.kg + config.grm]
            weight_total = Decimal(f'{kg}.{gr}')

            # Try to find the product by different barcode fields
            product = Inventory.objects.filter(
                barcode=str(item_code)
            ).first() or Inventory.objects.filter(
                manualbc__iexact=str(item_code)
            ).first() or Inventory.objects.filter(
                barcode2__endswith=str(item_code)
            ).first() or Inventory.objects.filter(
                inv_id = int(item_code)
                ).first()
            
        except Exception as e:
            # Optional: log the exception
            print(f"Weighted barcode error: {e}")

    return product, weight_total







def json_to_invoice(
    item=None,
    header_fields=None,
    fields_will_update=None,
    system_fields=None,
    is_header=False,
    update=False
):
    item = item or {}
    header_fields = header_fields or {}
    fields_will_update = fields_will_update or {}
    system_fields = system_fields or {}
    inv_id = item.get("inv_id")
    
    
    row_data = calculate_row_totals(item)


    #calculate last_pur_price and cost
    cost = calculate_cost(inv_id,row_data['qty'])
    

    # header_data = calculate_header_totals(header_fields,item)
    # print('header_data',header_data,'jakldjfklajdfkaj',header_fields)
    invoice_data = {
        # common
        "bill_no": fields_will_update.get("bill_no"),
        "is_header": is_header,

        "date": header_fields.get("date"),
        "dateent": fields_will_update.get("dateent"),
        "dateedit": now_karachi() if update else None,

        "user": fields_will_update.get("user", ""),
        "edit_by": system_fields.get("user", "") if update else None,
        "header_edit_count": fields_will_update.get(
            "header_edit_count", 0
        ) if update else 0,
        

        "company": system_fields.get("company"),
        "branch": system_fields.get("branch"),
        "posterminal": system_fields.get("posterminal"),

        # detail row fields
        "inv_id": item.get("inv_id"),
        "prod_name": item.get("prod_name", ""),
        "category": item.get("category", ""),

        "qty": row_data["qty"],
        "rate": row_data["rate"],

        "packing_mode": item.get(
            "packing_mode", 1
        ),
        "uom":item.get('uom',None),

        "pack_qty": Decimal(
            str(item.get("pack_qty", 0))
        ),

        "row_discount_percent":
            row_data["row_discount_percent"],

        "row_discount_amount":
            row_data["row_discount_amount"],

        "row_net_total":
            row_data["row_net_total"],

        "row_notes":
            item.get("row_notes", ""),

        "row_net_cost":
            (cost * (row_data["qty"] or 0)),

        "row_rate_cost":
            cost or 0,
    }

    if is_header:
        invoice_data.update(header_fields)

    return Invoice(**invoice_data)
