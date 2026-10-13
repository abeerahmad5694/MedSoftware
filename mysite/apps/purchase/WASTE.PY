

# D = lambda v: Decimal(str(v or 0))

# def calculate_purchase_row(item):
#     qty = D(item.get("qty"))
#     rate = D(item.get("rate"))
#     pack_qty = D(item.get("pack_qty", 1)) or Decimal('1')
    
#     # If rate is per pack, convert to base qty rate. If your rate is already per base, remove this
#     # gross = qty * rate * pack_qty
#     gross = qty * rate  # assuming rate is per base unit

#     disc1_p = D(item.get("row_discount_percent"))
#     disc1_a = D(item.get("row_discount_amount"))
#     if disc1_a == 0 and disc1_p > 0:
#         disc1_a = gross * disc1_p / Decimal('100')

#     disc2_p = D(item.get("row_discount_percent2", 0))
#     disc2_a = D(item.get("row_discount_amount2", 0))
#     after_disc1 = gross - disc1_a
#     if disc2_a == 0 and disc2_p > 0:
#         disc2_a = after_disc1 * disc2_p / Decimal('100')

#     net_total = gross - disc1_a - disc2_a
    
#     # Effective qty for costing
#     bonus = D(item.get("row_bonus", 0))

#     return {
#         "qty": qty,
#         "rate": rate,
#         "pack_qty": pack_qty,
#         "bonus": bonus,
#         "eff_qty": qty + bonus,
#         "gross_total": gross,
#         "row_discount_percent": disc1_p,
#         "row_discount_amount": disc1_a,
#         "row_discount_percent2": disc2_p,
#         "row_discount_amount2": disc2_a,
#         "row_net_total": net_total,
#     }



# def calculate_landed_cost(cart_items, header_fields):
#     # Pass 1: calc rows and total base
#     rows = [calculate_purchase_row(it) for it in cart_items]
#     total_net = sum((r["row_net_total"] for r in rows), Decimal('0'))
#     total_qty = sum((r["qty"] for r in rows), Decimal('0'))
    
#     # Avoid div by zero
#     total_net_safe = total_net if total_net != 0 else Decimal('1')

#     # Header addon pools
#     freight = D(header_fields.get("header_freight_amount"))
#     unload = D(header_fields.get("header_unload_amount"))
#     labour = D(header_fields.get("header_labour_amount"))
#     msc = D(header_fields.get("header_msc_charges"))
#     gst = D(header_fields.get("header_gst_amount"))
#     wht = D(header_fields.get("header_wht_amount"))
#     advtax = D(header_fields.get("header_advtax_amount"))
#     delivery = D(header_fields.get("header_delivery_charges"))
#     shortaccess = D(header_fields.get("header_shortaccess", 0))

#     total_addon = freight + unload + labour + msc + gst + wht + advtax + delivery + shortaccess
#     total_header_disc = D(header_fields.get("header_discount_amount"))

#     # Pass 2: allocate
#     final_rows = []
#     for r in rows:
#         # PROFESSIONAL: Allocation by Value. Best for accounting
#         ratio = r["row_net_total"] / total_net_safe

#         allocated_addon = total_addon * ratio
#         allocated_disc = total_header_disc * ratio

#         row_landed_total = r["row_net_total"] + allocated_addon - allocated_disc
        
#         # Per unit landed cost
#         if r["eff_qty"] > 0:
#             per_unit_cost = row_landed_total / r["eff_qty"]
#         else:
#             per_unit_cost = Decimal('0')

#         # Optional: if you want weight-based allocation for freight only
#         # if header_fields.get("header_weight") and total_qty > 0:
#         #    weight_ratio = r["qty"] / total_qty
#         #    freight_alloc = freight * weight_ratio
#         #    ...

#         r["row_landed_total"] = row_landed_total.quantize(Decimal('0.01'), ROUND_HALF_UP)

#         r["row_total_cost"]  = (per_unit_cost / (r.get('pack_qty',1) * r.get('qty',1)) if r.get('packing_mode') in [2,3] else per_unit_cost / r.get('qty',1)).quantize(Decimal('0.0001'), ROUND_HALF_UP)
        
#         r["allocated_addon"] = allocated_addon
#         r["allocated_discount"] = allocated_disc
#         final_rows.append(r)

#     return final_rows


# def calculate_row_totals(item):
#     """
#     Calculate a single invoice row.
#     """

#     qty = Decimal(str(item.get("qty", 0)))
#     rate = Decimal(str(item.get("rate", 0)))

#     gross_total = qty * rate

#     discount_percent = Decimal(
#         str(item.get("row_discount_percent", 0))
#     )

#     discount_amount = Decimal(
#         str(item.get("row_discount_amount", 0))
#     )

#     # Calculate amount from percent if amount not supplied
#     if discount_amount == 0 and discount_percent > 0:
#         discount_amount = (
#             gross_total * discount_percent
#         ) / Decimal("100")

#     net_total = gross_total - discount_amount

#     return {
#         "qty": qty,
#         "rate": rate,
#         "row_discount_percent": discount_percent,
#         "row_discount_amount": discount_amount,
#         "row_net_total": net_total,
#     }





# def calculate_header_totals(header_fields, items):
#     """
#     Calculate invoice header totals from detail rows.
#     """

#     item_total = Decimal("0")

#     for item in items:
#         row = calculate_row_totals(item)
#         item_total += row["row_net_total"]

#     total_items = len(items)

#     discount_percent = Decimal(
#         str(header_fields.get("header_discount_percent", 0))
#     )

#     discount_amount = Decimal(
#         str(header_fields.get("header_discount_amount", 0))
#     )

#     if discount_amount == 0 and discount_percent > 0:
#         discount_amount = (
#             item_total * discount_percent
#         ) / Decimal("100")

#     delivery_charges = Decimal(
#         str(header_fields.get("header_delivery_charges", 0))
#     )

#     gst_percent = Decimal(
#         str(header_fields.get("header_gst_percent", 0))
#     )

#     taxable_amount = (
#         item_total
#         - discount_amount
#         + delivery_charges
#     )

#     gst_amount = Decimal(
#         str(header_fields.get("header_gst_amount", 0))
#     )

#     if gst_amount == 0 and gst_percent > 0:
#         gst_amount = (
#             taxable_amount * gst_percent
#         ) / Decimal("100")

#     msc_charges = Decimal(
#         str(header_fields.get("header_msc_charges", 0))
#     )

#     net_total = (
#         taxable_amount
#         + gst_amount
#         + msc_charges
#     )

#     cash_paid = Decimal(
#         str(header_fields.get("header_cash_paid", 0))
#     )

#     bank_paid = Decimal(
#         str(header_fields.get("header_bank_paid", 0))
#     )

#     total_paid = Decimal(int(cash_paid) + int(bank_paid))

#     change_amount = max(
#         Decimal("0"),
#         total_paid - net_total
#     )

#     return {
#         "header_total_items": total_items,
#         "header_item_total": item_total,
#         "header_discount_percent": discount_percent,
#         "header_discount_amount": discount_amount,
#         "header_delivery_charges": delivery_charges,
#         "header_gst_percent": gst_percent,
#         "header_gst_amount": gst_amount,
#         "header_msc_charges": msc_charges,
#         "header_net_total": net_total,
#         "header_cash_paid": cash_paid,
#         "header_bank_paid": bank_paid,
#         "header_total_paid": total_paid,
#         "header_change_amount": change_amount,
#     }







# # def scan_barcode(request, code):
# #     # Ensure the user always has a BarcodConfig
# #     config, created = BarcodConfig.objects.get_or_create(
# #         user = 'main_bc',
# #         defaults={'price_base': 'N'}
# #     )
# #     # print(request.user)
# #     product = None
# #     weight_total = None

# #     try:
# #         # Fast exact match
# #         # product = Inventory.objects.filter(
# #         #     Q(barcode = str(code)) | Q(inv_id = int(code)) | Q(manualbc__iexact = str(code)) 
# #         # ).first()
# #         product = Inventory.objects.filter(manualbc__iexact=str(code)).first()

# #         if not product:
            
# #             product = Inventory.objects.filter(barcode=str(code)).first()
            
# #         if not product:
            

# #             product = Inventory.objects.filter(inv_id=int(code)).first()

        
            
# #         if product:
            

# #             return product, None
# #     except Exception as e:
# #         # Optional: log the exception
# #         print(f"Exact match error: {e}")

# #     # Weighted barcode
# #     if len(code) == config.total_bc_digits:
        
# #         try:
# #             trimmed = code[config.left_delete:len(code)-config.right_delete]
# #             item_code = trimmed[:config.item_bc]
# #             w = trimmed[config.item_bc:]
# #             kg = w[:config.kg]
# #             gr = w[config.kg:config.kg + config.grm]
# #             weight_total = Decimal(f'{kg}.{gr}')

# #             # Try to find the product by different barcode fields
# #             product = Inventory.objects.filter(
# #                 barcode=str(item_code)
# #             ).first() or Inventory.objects.filter(
# #                 manualbc__iexact=str(item_code)
# #             ).first() or Inventory.objects.filter(
# #                 barcode2__endswith=str(item_code)
# #             ).first() or Inventory.objects.filter(
# #                 inv_id = int(item_code)
# #                 ).first()
            
# #         except Exception as e:
# #             # Optional: log the exception
# #             print(f"Weighted barcode error: {e}")

# #     return product, weight_total




# from django.shortcuts import render
# from django.db import transaction

# # from django.db.models import Q
# from django.views.decorators.http import require_GET, require_POST
# # 
# # from django.core.paginator import Paginator, EmptyPage
# from django.views.decorators.csrf import csrf_exempt


# from decimal import Decimal
# import json
# from apps.purchase.models import Purchase
# from apps.myglobal.services.helpers import get_next_voucher
# from django.http import JsonResponse
# from apps.purchase.services.purchase_helpers import json_to_invoice ,now_karachi
# from apps.inventory.services.valuation import STOCK_IN, _reverse_voucher_stock
# # from apps.sale.services.
# from django.forms.models import model_to_dict
# from apps.purchase.services.purchase_calculations import calculate_landed_cost
# from apps.myledger.models import Vchno ,Gledg
# from apps.myledger.services.dto import GledgLineDTO
# from apps.myledger.services.voucher_utills import create_gledg_entries

# DEFAULT_LABOUR_PAYABLE_ACCOUNT = 231000123
# DEFAULT_FREIGHT_PAYABLE_ACCOUNT =231000124
# DEFAULT_UNLOAD_PAYABLE_ACCOUNT = 231000125
# DEFAULT_MY_CASH_ACCOUNT = 110000001
# DEFAULT_MY_BANK_ACCOUNT = 111000001
# DEFAULT_MY_CASH_CLIENT_ACCOUNT = 112000001



# @csrf_exempt
# @require_POST
# @transaction.atomic
# def save_bill(request):
#     user = request.user
#     fields_will_update = {}
#     system_fields = {}
#     update=False
   
#     try:
#         payload = json.loads(request.body.decode("utf-8"))
#     except:
#         return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

#     if isinstance(payload, dict):
#         payload = [payload]
#     elif not isinstance(payload, list):
#         return JsonResponse({"success": False, "message": "Invalid payload format"})


#     # print('palyod=============',payload)
#     # print('payment mode' ,payload[0]['header_payment_mode'])
#     for data in payload:
#         items = data.get("items", [])
        
#         if not items:
#             return JsonResponse({"success": False, "message": "No items provided"})
    
#         if data.get('bill_no'):
#             old_bill_no = int(data.get('bill_no'))
#             old_bill = Purchase.objects.filter(bill_no=old_bill_no, company = user.userprofile.company,branch = user.userprofile.branch)
#             if not old_bill:
#                 return JsonResponse({"success": False, "message": "Bill not found"})
#             old_item = old_bill.filter(is_header = True).first()
#             fields_will_update = {
#                 'dateent': old_item.dateent,
#                 'date':old_item.date if not data.get('date') else data.get('date'),
#                 'header_edit_count': old_item.header_edit_count + 1,
#                 'user': old_item.user,
#                 "bill_no":old_bill_no,
#             }
#             update = True
#             # Reverse existing stock lots BEFORE deleting the rows.
#             # Restores StockLot.quantity_remaining + Inventory.bal_qty atomically.
#             # Blocks edit if any lot was already partially sold.
#             try:
#                 _reverse_voucher_stock(
#                     company_id=user.userprofile.company.id,
#                     branch_id=user.userprofile.branch.id,
#                     voucher_type='PURCHASE',
#                     voucher_bill_no=old_bill_no,
#                     block_if_partially_sold=True,
#                 )
#             except ValueError as ve:
#                 return JsonResponse({"success": False, "message": str(ve)})
#             old_bill.delete()
            
#         else:
#             fields_will_update = {
#                 'dateent': now_karachi(),
#                 'date':now_karachi().date() if not data.get('date') else data.get('date'),
#                 'header_edit_count': 0,
#                 'user': user,
#                 "bill_no":get_next_voucher('PUR'),
#             }   

#         system_fields = {
#             "user": user,
#             "company": user.userprofile.company,
#             "branch": user.userprofile.branch,
#             "posterminal": user.userprofile.terminal,
#         }

#         landed_calcs = calculate_landed_cost(items, data)
#         is_return = data.get('is_return',False)
#         data.pop('local_id',None)
#         data.pop('items',None)
#         data.pop('date',None)
#         data.pop('is_return',None)
#         # Build Purchase rows + collect stock data in one O(N) pass
#         invoices = []
#         stock_rows = []   # (inv_id, base_qty, unit_cost_per_base, expiry_date)
#         return_amount=0
#         positive_amount=0

#         purchase_date = fields_will_update.get('date')
#         bill_no = fields_will_update.get('bill_no')

#         for index, (item, landed) in enumerate(zip(items, landed_calcs)):
#             is_first = (index == 0)
#             return_amount += abs(item.get("row_net_total")) if int(item.get("row_net_total")) < 0 else 0
#             positive_amount += item.get("row_net_total") if int(item.get("row_net_total")) > 0 else 0
#             # (positive_amount >0 or data.get('header_freight_amount')>0 or data.get('header_labour_amount')>0 or data.get('header_unload_amount')>0 )
#             if is_return and  positive_amount > 0 :
#                 return JsonResponse({"success": False, "message": f"Positive Qty not allowed {item.get('inv_id')}. For Return Switch To Purchase Return"})

#             elif not is_return and (return_amount > 0 or (Decimal(data.get('header_freight_amount') or 0) < 0) or (Decimal(data.get('header_labour_amount') or 0) < 0) or (Decimal(data.get('header_unload_amount') or 0) < 0 )) :

#                 return JsonResponse({"success": False, "message": f"Negative Qty not allowed {item.get('inv_id')}. For Return Switch To Purchase Return"})
            
#             invoices.append(json_to_invoice(
#                 item=item, 
#                 header_fields=data if is_first else {}, 
#                 fields_will_update=fields_will_update,
#                 system_fields=system_fields,
#                 is_header=is_first, 
#                 update=update,
#                 landed_calc=landed
#             ))

#             # Collect stock data for every row (header row also has item)
#             inv_id = item.get('inv_id')
#             if inv_id:
#                 base_qty = Decimal(str(item.get('qty', 0))) * Decimal(str(item.get('pack_qty', 1)))
#                 unit_cost_per_base = Decimal(str(landed.get('row_total_cost_per_base_unit', 0) or 0))
#                 expiry_date = item.get('row_expiry_dt') or None
#                 stock_rows.append((inv_id, base_qty, unit_cost_per_base, expiry_date))

#         # Bulk insert all Purchase rows first
#         Purchase.objects.bulk_create(invoices)

#         # Call STOCK_IN for each item row — creates StockLot + StockLedger, updates bal_qty
#         for inv_id, base_qty, unit_cost_per_base, expiry_date in stock_rows:
#             if base_qty == 0:
#                 continue
#             try:
#                 STOCK_IN(
#                     company_id=user.userprofile.company.id,
#                     branch_id=user.userprofile.branch.id,
#                     inventory_item_id=inv_id,
#                     base_quantity=abs(base_qty),
#                     rate_cost_per_unit=unit_cost_per_base,
#                     voucher_date=purchase_date,
#                     voucher_type='PURCHASE',
#                     voucher_bill_no=bill_no,
#                     voucher_row_id=None,
#                     expiry_date=expiry_date,
#                     is_update=False,  # reversal already done above before old_bill.delete()
#                 )
#             except Exception as stock_err:
#                 print(f'[STOCK_IN] Error for inv_id={inv_id}: {stock_err}')
#         #create gledg entries        
        
#         if Decimal(str(data.get('header_total_paid') or "0")) not in ( Decimal("0"),Decimal("1")):
#             my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else int(data.get('header_payment_mode'))
#             # v_types = ['CP']
#             # if return_amount !=0:   
#             #     v_types.append('CR')
#             # elif str(data.get('header_payment_mode')).startswith('111'):
#             #     v_types = ["BR"]

            
#             v_type = 'CP' if not str(data.get('header_payment_mode')).startswith('111') else 'BP'
#             if is_return:
#                 v_type = 'CR' if not str(data.get('header_payment_mode')).startswith('111') else 'BR'
#             # print('mycountacc',my_counter_account , 'v_type',v_type)
#             lines = [
#                 GledgLineDTO(
#                     accCode=int(data.get('header_acc_code') or 0),
#                     head=data.get('head') or "",
#                     notes= f"PUR# {fields_will_update.get('bill_no')}" if not is_return else f"PUR RETURN# {fields_will_update.get('bill_no')}",
#                     receiptNo = 0,
#                     chqNo = '0',
#                     amount = Decimal(abs(Decimal(data.get('header_total_paid')))).quantize(Decimal("0.000")),
#                     # amount = Decimal(positive_amount).quantize(Decimal("0.000")) if not is_return else Decimal(abs(return_amount)).quantize(Decimal("0.000")),
#                     refAccCode = my_counter_account,
#                     amtType = "DR" if not is_return else "CR",
#                 ),
#             ]

#             if Decimal(str(data.get("header_freight_amount") or "0")) != Decimal("0"):
#                 lines.append(
#                     GledgLineDTO(
#                         accCode=int(DEFAULT_FREIGHT_PAYABLE_ACCOUNT or 0) if not data.get('header_freight_acc_code') else int(data.get('header_freight_acc_code')),
#                         head=data.get('head') or "",
#                         notes= f"PUR# {fields_will_update.get('bill_no')}",
#                         receiptNo = 0,
#                         chqNo = '0',
#                         amount = Decimal(abs(Decimal(data.get('header_freight_amount')))).quantize(Decimal("0.000")),
#                         refAccCode = my_counter_account,
#                         amtType = "DR" if Decimal(data.get('header_freight_amount')) > 0 else 'CR',
#                     ),
#                 )

#             if Decimal(str(data.get("header_labour_amount") or "0")) != Decimal("0"):
#                 lines.append(
#                     GledgLineDTO(
#                         accCode=int(DEFAULT_LABOUR_PAYABLE_ACCOUNT or 0) if not data.get('header_labour_acc_code') else int(data.get('header_labour_acc_code')),
#                         head=data.get('head') or "",
#                         notes= f"PUR# {fields_will_update.get('bill_no')}",
#                         receiptNo = 0,
#                         chqNo = '0',
#                         amount = Decimal(abs(Decimal(data.get('header_labour_amount')))).quantize(Decimal("0.000")),
#                         refAccCode = my_counter_account,
#                         amtType = "DR" if Decimal(data.get('header_labour_amount')) > 0 else 'CR',
#                     ),
#                 )

#             if Decimal(str(data.get("header_unload_amount") or "0")) != Decimal("0"):
#                 lines.append(
#                     GledgLineDTO(
#                         accCode=int(DEFAULT_UNLOAD_PAYABLE_ACCOUNT or 0) if not data.get('header_unload_acc_code') else int(data.get('header_unload_acc_code')),
#                         head=data.get('head') or "",
#                         notes= f"PUR# {fields_will_update.get('bill_no')}",
#                         receiptNo = 0,
#                         chqNo = '0',
#                         amount = Decimal(abs(Decimal(data.get('header_unload_amount')).quantize(Decimal("0.000")))),
#                         refAccCode = my_counter_account,
#                         amtType = "DR" if Decimal(data.get('header_unload_amount')) > 0 else 'CR',
#                     ),
#                 )
            
#             if update:
#                 old_gledg = Gledg.objects.filter(PUR_INV='P',INVOICE_ID=fields_will_update.get('bill_no')).only('VNO').first()
#                 if not old_gledg:
#                     return JsonResponse({"success": False, "message": "Purchase invoice does not exists in ledger"})
            
#             created, message, _vno = create_gledg_entries(
#                 request = request,
#                 lines=lines,
#                 date=fields_will_update.get('dateent'),
#                 v_type=v_type,
#                 remarks='',
#                 pur_inv='P',
#                 update=update,
#                 vno_to_update = old_gledg.VNO if update and old_gledg else 0,
#                 inv_id=fields_will_update.get('bill_no'),
#                 called_by_invoices = True,

#             )
#             if not created:
#                 raise Exception(f"Ledger creation failed: {message}")
#     synced = []
#     return JsonResponse({
#         "success": True,"synced_bills": synced,"bill_no":fields_will_update.get('bill_no')
        
#     })





# def get_bill(request,bill_no):
#     user = request.user
#     if not bill_no:
#         return JsonResponse({"success": False, "message": "Invalid bill_no"})

#     try:
#         bill = Purchase.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
#         # print('bill=============================',bill)
#         if not bill:
#             return JsonResponse({"success": False, "message": "Bill not found"})
#     except Exception as e:
#         return JsonResponse({"success": False, "message": str(e)})
#     # header_row = bill.filter(is_header = True).first()
#     # items = bill.filter(is_header = False)
#     try:
#         item_list = []
#         for item in bill:
#             if item.is_header:
#                 data_list = {
#                 "bill_no":item.bill_no,
#                 "branch":str(item.branch),
#                 "category":str(item.category),
#                 "company":str(item.company),
#                 "posterminal" :str(item.posterminal),
#                 "date":item.date,
#                 "dateedit":item.dateedit,
#                 "edit_by":item.edit_by,
#                 "header_bank_paid":item.header_bank_paid,
#                 "header_card_last4":item.header_card_last4,
#                 "header_cash_paid":item.header_cash_paid,
#                 "header_change_amount":item.header_change_amount,
#                 "header_delivery_charges":item.header_delivery_charges,
#                 "header_discount_amount":item.header_discount_amount,
#                 "header_discount_percent":item.header_discount_percent,
#                 "header_edit_count":item.header_edit_count,
#                 "header_gst_amount":item.header_gst_amount,
#                 "header_gst_percent":item.header_gst_percent,
#                 "header_item_total":item.header_item_total,
#                 "header_msc_charges":item.header_msc_charges,
#                 "header_net_total":item.header_net_total,
#                 "header_payment_mode":item.header_payment_mode,
#                 "header_remarks":item.header_remarks,
#                 'date':item.date.strftime('%m-%d-%Y') if item.date else None,
#                 'header_supl_inv_no':item.header_supl_inv_no,
#                 'header_supl_inv_date':item.header_supl_inv_date.strftime('%m-%d-%Y') if item.header_supl_inv_date else None,
#                 'header_our_ref':item.header_our_ref,
#                 'header_our_ref_date':item.header_our_ref_date.strftime('%m-%d-%Y') if item.header_our_ref_date else None,
#                 'header_delivery_person':item.header_delivery_person,
#                 'header_freight_amount':item.header_freight_amount,
#                 'header_labour_amount':item.header_labour_amount,
#                 'header_unload_amount':item.header_unload_amount,
#                 "header_total_items":item.header_total_items,
#                 "header_total_paid" :item.header_total_paid,
#                 "user" :str(item.user),
#                 "salesman" :item.salesman,
#                 "is_header":item.is_header,
#                 "header_acc_code":item.header_acc_code,
#             }
#             item_list.append({
#                 "inv_id":item.inv_id,
#                 "pack_qty" :item.pack_qty,
#                 "packing_mode" :item.packing_mode,
#                 "prod_name" :item.prod_name,
#                 "qty" :item.qty,
#                 "rate" :item.rate,
#                 "row_discount_amount" :item.row_discount_amount,
#                 "row_discount_percent" :item.row_discount_percent,
#                 "row_net_total" :item.row_net_total,
#                 "row_notes" :item.row_notes,
#                 "uom" :item.uom,
#                 'row_expiry_dt':item.row_expiry_dt.strftime('%Y-%m-%d') if item.row_expiry_dt else None,
#                 'row_batch_no':item.row_batch_no if item.row_batch_no else None,

#                 })
#         data_list['items']=item_list
#         # print('data_list======================',item_list)
#     except Exception as e:
#         return JsonResponse({"success": False, "message": str(e)})
#     # print('dtataa===================',data_list)
#     return JsonResponse({"success": True,"data": data_list,"message":'Successfully Loaded!'})




    
# from apps.sale.services.sale_calculations import calculate_row_totals, calculate_header_totals
# from decimal import Decimal
# from apps.purchase.models import Purchase 
# def now_karachi():
#     from apps.myglobal.services.helpers import DateTimeHelper
#     return DateTimeHelper().get_server_time()

# from datetime import datetime







# def json_to_invoice(
#     item=None,
#     header_fields=None,
#     fields_will_update=None,
#     system_fields=None,
#     is_header=False,
#     update=False
# ):
#     item = item or {}
#     header_fields = header_fields or {}
#     fields_will_update = fields_will_update or {}
#     system_fields = system_fields or {}
#     calculate_simple_cost = False
#     # print('dkafdlajfdklajflk',header_fields)
#     row_data = calculate_row_totals(item)
#     # header_data = calculate_header_totals(header_fields,item)
#     # print('header_data',header_data,'jakldjfklajdfkaj',header_fields)





#     # thats wron bcz these header amounts are for all items in the cart so adding them for one item cost is wrong i have to calculate average or allocated ammounts first first 
#     row_total_cost = (
#         row_data['row_net_total']  + 
#         header_fields.get("header_freight_amount", 0) +
#         header_fields.get("header_unload_amount", 0)+ 
#         header_fields.get("header_labour_amount", 0) +
#         header_fields.get("header_msc_charges", 0) +
#         header_fields.get("header_gst_amount", 0) - 
#         header_fields.get("header_discount_amount", 0) 
#         ) if not calculate_simple_cost else (row_data['row_net_total'] / row_data['qty'])






#     invoice_data = {
#         # common
#         "bill_no": fields_will_update.get("bill_no"),
#         "is_header": is_header,

#         # "date": header_fields.get("date"),
#         "dateent": fields_will_update.get("dateent"),
#         "dateedit": now_karachi() if update else None,

#         "user": fields_will_update.get("user", ""),
#         "edit_by": system_fields.get("user", "") if update else None,
#         "header_edit_count": fields_will_update.get(
#             "header_edit_count", 0
#         ) if update else 0,
        

#         "company": system_fields.get("company"),
#         "branch": system_fields.get("branch"),
#         "posterminal": system_fields.get("posterminal"),

#         # detail row fields
#         "inv_id": item.get("inv_id"),
#         "prod_name": item.get("prod_name", ""),
#         "category": item.get("category", ""),

#         "qty": row_data["qty"],
#         "rate": row_data["rate"],

#         "packing_mode": item.get(
#             "packing_mode", 1
#         ),
#         "uom":item.get('uom',None),

#         "pack_qty": Decimal(
#             str(item.get("pack_qty", 0))
#         ),

#         "row_discount_percent":
#             row_data["row_discount_percent"],

#         "row_discount_amount":
#             row_data["row_discount_amount"],

#         "row_net_total":
#             row_data["row_net_total"],

#         "row_notes":
#             item.get("row_notes", ""),
#         "row_batch_no":
#             item.get("row_batch_no", ""),
#         "row_expiry_dt":
#             datetime.strptime(item.get("row_expiry_dt"), '%Y-%m-%d').date() if item.get('row_expiry_dt')!=None and item.get('row_expiry_dt')!="" else None,
#         'row_notes':item.get("row_notes", ""),
#     }

#     if is_header:
#         invoice_data.update(header_fields)

#     return Purchase(**invoice_data)
