



# from apps.myglobal.services.helpers import get_user_perms
# from django.db import transaction
# from django.views.decorators.http import require_GET, require_POST
# from django.views.decorators.csrf import csrf_exempt
# from decimal import Decimal
# import json
# from apps.sale.models import Invoice
# from apps.myglobal.services.helpers import get_next_voucher
# from django.http import JsonResponse
# from apps.sale.services.helpers import json_to_invoice ,now_karachi
# from apps.myledger.models import Vchno ,Gledg
# from apps.myledger.services.dto import GledgLineDTO
# from apps.myledger.services.voucher_utills import create_gledg_entries
# from apps.purchase.services.purchase_helpers import handle_inventory_valuation  # kept for fallback
# from apps.inventory.services.valuation import STOCK_OUT, _reverse_voucher_stock
# from apps.configuration.selectors import get_company_config, get_default_account_code
# from apps.inventory.models import Inventory
# from apps.purchase.models import Purchase
# from apps.quotation.models import Quotation


# DEFAULT_LABOUR_PAYABLE_ACCOUNT = 231000123
# DEFAULT_FREIGHT_PAYABLE_ACCOUNT = 231000124
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


#     for data in payload:
#         items = data.get("items", [])

#         # print('this is items: ',items)
    
#         if not items:
#             return JsonResponse({"success": False, "message": "No items provided"})

#         # --- Server-side discount & negative sale policy enforcement (security layer) ---
#         try:
#             user_profile = getattr(user, 'userprofile', None)
#             company = getattr(user_profile, 'company', None)
#             branch = getattr(user_profile, 'branch', None)
#             pos_config, _ = get_company_config(
#                 company.id if company else None,
#                 branch.id if branch else None
#             )
#             pos_cfg = pos_config.get('pos', {})
#             row_discount_allowed = bool(pos_cfg.get('row_discount_allowed', True))
#             max_row_disc_pct  = float(pos_cfg.get('max_row_discount_percent', 0) or 0)
#             max_row_disc_amt  = float(pos_cfg.get('max_row_discount_amount', 0) or 0)
#             max_total_disc_pct = float(pos_cfg.get('max_total_discount_percent', 0) or 0)
#             allow_negative_sale = bool(pos_cfg.get('allow_negative_sale', False))

#             # Validate / sanitize per-row discounts and negative sale
#             for item in items:
#                 if item.get('qty') < 0:
#                     has_permission, message = get_user_perms(request, "return_sale")
#                     if not has_permission:
#                         return JsonResponse({'success': False, 'message': message}, status=200)

#                 if not row_discount_allowed:
#                     item['row_discount_percent'] = 0
#                     item['row_discount_amount'] = 0
#                     row_disc_pct = 0
#                     row_disc_amt = 0
#                 else:
#                     qty = float(item.get('qty') or 0)
#                     rate = float(item.get('rate') or 0)
#                     gross = qty * rate
#                     row_disc_pct = float(item.get('row_discount_percent') or 0)
#                     row_disc_amt = float(item.get('row_discount_amount') or 0)

#                     # Validate max_row_discount_percent
#                     if max_row_disc_pct > 0:
#                         if row_disc_pct > max_row_disc_pct:
#                             return JsonResponse({
#                                 "success": False,
#                                 "message": f"Row discount {row_disc_pct}% exceeds allowed limit of {max_row_disc_pct}%"
#                             }, status=403)
#                         if row_disc_amt > 0 and gross > 0:
#                             effective_pct = (row_disc_amt / gross) * 100
#                             if effective_pct > max_row_disc_pct:
#                                 return JsonResponse({
#                                     "success": False,
#                                     "message": f"Row discount Rs {row_disc_amt} ({effective_pct:.2f}%) exceeds allowed limit of {max_row_disc_pct}%"
#                                 }, status=403)

#                     # Validate max_row_discount_amount
#                     if max_row_disc_amt > 0:
#                         if row_disc_amt > max_row_disc_amt:
#                             return JsonResponse({
#                                 "success": False,
#                                 "message": f"Row discount Rs {row_disc_amt} exceeds allowed limit of Rs {max_row_disc_amt}"
#                             }, status=403)
#                         if row_disc_pct > 0 and gross > 0:
#                             effective_amt = (gross * row_disc_pct) / 100
#                             if effective_amt > max_row_disc_amt:
#                                 return JsonResponse({
#                                     "success": False,
#                                     "message": f"Row discount {row_disc_pct}% (Rs {effective_amt:.2f}) exceeds allowed limit of Rs {max_row_disc_amt}"
#                                 }, status=403)

#                 # Negative sale verification
#                 if not allow_negative_sale and item.get('inv_id'):
#                     qty = int(item.get('qty') or 0)
#                     pack_qty = int(item.get('pack_qty') or 1)
#                     req_base_qty = qty * pack_qty
#                     old_base_qty = int(item.get('row_old_total_base_qty') or 0) if data.get('bill_no') else 0
#                     net_qty_deducted = req_base_qty - old_base_qty
#                     if net_qty_deducted > 0:
#                         inv_obj = Inventory.objects.filter(inv_id=item.get('inv_id')).first()
#                         if inv_obj and (inv_obj.bal_qty or 0) < net_qty_deducted:
#                             return JsonResponse({
#                                 "success": False,
#                                 "message": f"Negative sale not allowed. Insufficient stock for '{item.get('prod_name', 'Item')}'. Available: {inv_obj.bal_qty or 0}, Required: {net_qty_deducted}"
#                             }, status=403)

#             # Validate total bill discount
#             if max_total_disc_pct > 0:
#                 header_disc_pct = float(data.get('header_discount_percent') or 0)
#                 if header_disc_pct > max_total_disc_pct:
#                     return JsonResponse({
#                         "success": False,
#                         "message": f"Total bill discount {header_disc_pct}% exceeds allowed limit of {max_total_disc_pct}%"
#                     }, status=403)

#             # Enforce delivery_charges_allowed: wipe delivery charges if not allowed
#             if not bool(pos_cfg.get('delivery_charges_allowed', True)):
#                 data['header_delivery_charges'] = 0

#             # Enforce tax_charges_allowed: wipe GST if not allowed
#             if not bool(pos_cfg.get('tax_charges_allowed', True)):
#                 data['header_gst_percent'] = 0
#                 data['header_gst_amount'] = 0

#             # Enforce msc_charges_allowed: wipe misc charges if not allowed
#             if not bool(pos_cfg.get('msc_charges_allowed', True)):
#                 data['header_msc_charges'] = 0

#             # Enforce require_remarks
#             if bool(pos_cfg.get('require_remarks', False)):
#                 if not str(data.get('header_remarks') or '').strip():
#                     return JsonResponse({
#                         "success": False,
#                         "message": "Remarks are required before saving the bill."
#                     }, status=403)

#         except Exception as policy_err:
#             # Non-blocking: log but don't crash on config errors
#             print(f'[save_bill] Policy check error: {policy_err}')
#         # --- End security enforcement ---

#         if data.get('bill_no'):
#             has_permission, message = get_user_perms(request, "edit_invoice")
#             if not has_permission:
#                 return JsonResponse({'success': False, 'message': message}, status=200)

#             old_bill_no = int(data.get('bill_no'))
#             old_bill = Invoice.objects.filter(bill_no=old_bill_no, company=user.userprofile.company, branch=user.userprofile.branch)
#             if not old_bill:
#                 return JsonResponse({"success": False, "message": "Bill not found"})
#             old_item = old_bill.filter(is_header=True).first()
#             fields_will_update = {
#                 'dateent': old_item.dateent,
#                 'date': old_item.date,
#                 'header_edit_count': old_item.header_edit_count + 1,
#                 'user': old_item.user,
#                 "bill_no": old_bill_no,
#             }
#             update = True
#             # Reverse stock issued for this invoice BEFORE deleting the rows.
#             # This restores StockLot.qty_remaining and Inventory.bal_qty atomically.
#             try:
                
#                 for v_type in ('SALE', 'SALE_RETURN'):
#                     _reverse_voucher_stock(
#                         company_id=user.userprofile.company.id,
#                         branch_id=user.userprofile.branch.id,
#                         voucher_type=v_type,
#                         voucher_bill_no=old_bill_no,
#                         block_if_partially_sold=False,
#                     )
#                 old_bill.delete()
#             except Exception as e:
#                 return JsonResponse({"success": False, "message": str(e)})
            
            
#         else:
#             fields_will_update = {
#                 'dateent': now_karachi(),
#                 'date':now_karachi().date() if not data.get('date') else data.get('date'),
#                 'header_edit_count': 0,
#                 'user': user,
#                 "bill_no":get_next_voucher('INV'),
#             }

#         system_fields = {
#             "user": user,
#             "company": user.userprofile.company,
#             "branch": user.userprofile.branch,
#             "posterminal": user.userprofile.terminal,
#         }
#         data.pop('local_id',None)
#         data.pop('items',None)
 
#         sale_date = fields_will_update.get('date')
#         bill_no = fields_will_update.get('bill_no')

#         # Build Invoice rows + collect stock data in one pass (O(N))
#         invoices = []
#         stock_rows = []  # (inv_id, base_qty, row_index)
#         return_amount = 0
#         positive_amount = 0

#         for index, item in enumerate(items):
#             first_item = (index == 0)
#             return_amount += abs(item.get("row_net_total")) if int(item.get("row_net_total")) < 0 else 0
#             positive_amount += item.get("row_net_total") if int(item.get("row_net_total")) > 0 else 0
#             if first_item:
#                 invoices.append(json_to_invoice(item=item, header_fields=data, fields_will_update=fields_will_update, system_fields=system_fields, is_header=True, update=update))
#             else:
#                 invoices.append(json_to_invoice(item=item, fields_will_update=fields_will_update, system_fields=system_fields, update=update))

#             # Collect stock info for every row (including header which also has item)
#             inv_id = item.get('inv_id')
#             if inv_id:
#                 base_qty = Decimal(str(item.get('qty', 0))) * Decimal(str(item.get('pack_qty', 1)))
#                 stock_rows.append((inv_id, base_qty, index))

        
#         with transaction.atomic():    
#             Invoice.objects.bulk_create(invoices)
            
            

#             # Issue stock and capture COGS per row; bulk-update row_net_cost / row_rate_cost
#             cogs_updates = []  # list of (inv_obj, total_cogs, per_unit_cogs)
#             created_invoices = list(Invoice.objects.filter(
#                 bill_no=bill_no,
#                 company=user.userprofile.company,
#                 branch=user.userprofile.branch
#             ).order_by('id'))
            
#             for inv_id, base_qty, row_index in stock_rows:
#                 if base_qty == 0:
#                     continue
#                 try:
                    
#                     row_obj = created_invoices[row_index]  # <- real row with PK
#                     voucher_row_id = row_obj.id 
#                     if base_qty > 0:
#                         total_cogs, per_unit_cogs = STOCK_OUT(
#                             company_id=user.userprofile.company.id,
#                             branch_id=user.userprofile.branch.id,
#                             inventory_item_id=inv_id,
#                             base_quantity_required=base_qty,
#                             voucher_date=sale_date,
#                             voucher_type='SALE',
#                             voucher_bill_no=bill_no,
#                             voucher_row_id=voucher_row_id,
#                             is_update=False,  # reversal done above before old_bill.delete()
#                         )
#                     else:
#                         total_cogs, per_unit_cogs = STOCK_OUT(
#                             company_id=user.userprofile.company.id,
#                             branch_id=user.userprofile.branch.id,
#                             inventory_item_id=inv_id,
#                             base_quantity_required=base_qty,
#                             voucher_date=sale_date,
#                             voucher_type='SALE_RETURN',
#                             voucher_bill_no=bill_no,
#                             voucher_row_id=voucher_row_id,
#                             is_update=False,  # reversal done above before old_bill.delete()
#                         )
                        
#                     # Match created row by row_index order (same order as items list)
#                     if row_index < len(created_invoices):
#                         row_obj = created_invoices[row_index]
#                         row_obj.row_net_cost = total_cogs
#                         row_obj.row_rate_cost = per_unit_cogs
#                         cogs_updates.append(row_obj)
#                 except Exception as stock_err:
#                     print(f'[STOCK_OUT] Error for inv_id={inv_id}: {stock_err}')

#             if cogs_updates:
#                 Invoice.objects.bulk_update(cogs_updates, ['row_net_cost', 'row_rate_cost'])


#         response = JsonResponse({"success": True, "header_voucher_no": bill_no})


#         if Decimal(str(data.get('header_total_paid') or "0")) not in [None,0,Decimal("0")] :
#             # my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else int(data.get('header_payment_mode'))
#             my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else DEFAULT_MY_BANK_ACCOUNT
#             v_types = ['CR']
#             if int(data.get('header_total_paid')) < 0:
#                 # v_types.append('CP')
#                 v_types = ['CP']
#             elif str(data.get('header_payment_mode')).startswith('111'):
#                 v_types = ["BR"]
#             # 'CR' if not str(data.get('header_payment_mode')).startswith('111') else 'BR'

#             lines = [];
#             return_lines = []
#             default_cash_client_acc = get_default_account_code('cash_client_acc', company.id if company else None, branch.id if branch else None)

#             if int(data.get('header_total_paid')) != 0:
#                 lines.append(GledgLineDTO(
#                     accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
#                     head=data.get('head') or "",
#                     notes= f"INV# {fields_will_update.get('bill_no')}" if int(data.get('header_total_paid'))>0 else f"INV RETURN# {fields_will_update.get('bill_no')}",
#                     receiptNo = 0,
#                     chqNo = '0',
#                     amount = Decimal(abs(Decimal(data.get('header_total_paid')))).quantize(Decimal("0.000")),
#                     # amount = Decimal(int(positive_amount)).quantize(Decimal("0.000")),
#                     refAccCode = my_counter_account,
#                     amtType = "DR" if int(data.get('header_total_paid')) < 0 else 'CR' ,
#                 ) )


#             # if return_amount != 0 and False:
#             #     return_lines.append(
#             #         GledgLineDTO(
#             #         accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
#             #         head=data.get('head') or "",
#             #         notes= f"INV RETURN# {fields_will_update.get('bill_no')}" ,
#             #         receiptNo = 0,
#             #         chqNo = '0',
#             #         # amount = Decimal(int(data.get('header_total_paid'))).quantize(Decimal("0.000")),
#             #         amount = Decimal(int(return_amount)).quantize(Decimal("0.000")),
#             #         refAccCode = my_counter_account,
#             #         amtType = "DR",
#             #     ))
            
            
#             if lines or return_lines:    
#                 old_positive_vno = 0
#                 old_gledg = {}
#                 if update:
#                     old_gledg = (
#                         Gledg.objects
#                         .filter(
#                             PUR_INV='I',
#                             INVOICE_ID=fields_will_update.get('bill_no'),
#                             AMT_TYPE='DR',
#                             V_TYPE__in=['CP', 'CR', 'BR'],
#                         )
#                         .values_list('VNO', 'V_TYPE')
#                     )


#                     for vno, v_type in old_gledg:
#                         if v_type == 'CP':
#                             old_return_vno = vno

#                         elif v_type in ['CR', 'BR']:
#                             old_positive_vno = vno
#                     # print('old_return_vno',old_gledg)
#                     # print('old_return_vno',old_gledg)


#                 for v_type in v_types:
                    
#                     created, message, _vno = create_gledg_entries(
#                         request = request,
#                         lines=lines,
#                         # lines=lines if v_type != 'CP' else return_lines,
#                         date=fields_will_update.get('dateent'),
#                         v_type=v_type,
#                         remarks='',
#                         pur_inv='I',
#                         update=update if update and len(old_gledg) >= 1 else False,
#                         # vno_to_update = old_gledg.VNO if update and old_gledg else 0,
#                         vno_to_update = old_return_vno if update and v_type =='CP' and len(old_gledg) >= 1 else old_positive_vno,
#                         inv_id=fields_will_update.get('bill_no'),
#                         called_by_invoices = True,
                        
                        
#                     ) 
#                     if not created:
#                         raise Exception(f"Ledger creation failed: {message}") 

#     synced = []
#     header_voucher_no = fields_will_update.get('bill_no')
#     return JsonResponse({
#         "success": True,"synced_bills": synced,"header_voucher_no":header_voucher_no

        
#     })





# def get_bill(request,bill_no):
    
    
#     has_permission, message = get_user_perms(request, "edit_invoice")
#     if not has_permission:
#         return JsonResponse({'success': False, 'message': message}, status=200)

    
#     user = request.user
#     if not bill_no:
#         return JsonResponse({"success": False, "message": "Invalid bill_no"})

#     try:
#         bill = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
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
#             })
#         data_list['items']=item_list
#         # print('data_list======================',item_list)
#     except Exception as e:
#         return JsonResponse({"success": False, "message": str(e)})
#     # print('dtataa===================',data_list)
#     return JsonResponse({"success": True,"data": data_list,"message":'Successfully Loaded!'})






# # @api_view(["POST"])
# @csrf_exempt
# @transaction.atomic

# def delete_sale_bill(request,pur_inv,bill_no):
#     try:
#         user = request.user
#         company = user.userprofile.company
#         branch = user.userprofile.branch
#         if not user.is_authenticated:
#             return JsonResponse({"success": False, "message": "User not authenticated"})
#         if not company:
#             return JsonResponse({"success": False, "message": "Company not found"})
#         if not branch:
#             return JsonResponse({"success": False, "message": "Branch not found"})

#         if not pur_inv or not bill_no:
#             return JsonResponse({"success": False, "message": "Pur inv or bill no not found"})

#         if pur_inv == 'I':
#             invoice = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
#             if not invoice:
#                 return JsonResponse({"success": False, "message": "Invoice not found"})

            
#             try:
                
#                 for v_type in ('SALE', 'SALE_RETURN'):
#                     _reverse_voucher_stock(
#                         company_id=user.userprofile.company.id,
#                         branch_id=user.userprofile.branch.id,
#                         voucher_type=v_type,
#                         voucher_bill_no=bill_no,
#                         block_if_partially_sold=False,
#                     )
                
            
#             except Exception as e:
#                 return JsonResponse({"success": False, "message": str(e)})
            
            
            
#             gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = invoice.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
#             if gledg_rows:
#                 gledg_rows.delete()
                
#             invoice.delete()

#         elif pur_inv == 'Q':
#             quotation = Quotation.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
#             if not quotation:
#                 return JsonResponse({"success": False, "message": "Quotation not found"})
            
            
#             quotation.delete()

#         elif pur_inv == 'P':
#             purchase = Purchase.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
#             if not purchase:
#                 return JsonResponse({"success": False, "message": "Purchase not found"})

#             gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = purchase.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
            
            
#             try:
                
#                 for v_type in ('PURCHASE','PURCHASE_RETURN'):
#                     _reverse_voucher_stock(
#                         company_id=user.userprofile.company.id,
#                         branch_id=user.userprofile.branch.id,
#                         voucher_type=v_type,
#                         voucher_bill_no=bill_no,
#                         block_if_partially_sold=True,
#                     )
                
                
            
#             except Exception as e:
#                 return JsonResponse({"success": False, "message": str(e)})
            
            
#             if gledg_rows:
#                 gledg_rows.delete()
                
#             purchase.delete()
            
#         return JsonResponse({"success": True,"message":'Successfully Deleted!'})

#     except Exception as e:
#         return JsonResponse({"success": False, "message": f"Error deletingd bill: {str(e)}"})
    
    
    

    
    
    
# # from django.shortcuts import render
# # from django.db import transaction
# # from django.views.decorators.http import require_GET, require_POST
# # from django.views.decorators.csrf import csrf_exempt
# # from decimal import Decimal
# # import json
# # from apps.sale.models import Invoice
# # from apps.myglobal.services.helpers import get_next_voucher
# # from django.http import JsonResponse
# # from apps.sale.services.helpers import json_to_invoice ,now_karachi
# # from django.forms.models import model_to_dict
# # from apps.myledger.models import Gledg
# # from apps.myledger.models import Vchno ,Gledg
# # from apps.myledger.services.dto import GledgLineDTO
# # from apps.myledger.services.voucher_utills import create_gledg_entries
# # from apps.purchase.services.purchase_helpers import handle_inventory_valuation
# # from apps.inventory.services.valuation import STOCK_IN, STOCK_OUT, _reverse_voucher_stock
# # from apps.configuration.selectors import get_company_config, get_default_account_code
# # from apps.inventory.models import Inventory
# # from apps.purchase.models import Purchase
# # from apps.quotation.models import Quotation


# # DEFAULT_LABOUR_PAYABLE_ACCOUNT = 231000123
# # DEFAULT_FREIGHT_PAYABLE_ACCOUNT = 231000124
# # DEFAULT_UNLOAD_PAYABLE_ACCOUNT = 231000125
# # DEFAULT_MY_CASH_ACCOUNT = 110000001
# # DEFAULT_MY_BANK_ACCOUNT = 111000001
# # DEFAULT_MY_CASH_CLIENT_ACCOUNT = 112000001


# # @csrf_exempt
# # @require_POST
# # @transaction.atomic
# # def save_bill(request):
# #     user = request.user
# #     fields_will_update = {}
# #     system_fields = {}
# #     update=False
   
# #     try:
# #         payload = json.loads(request.body.decode("utf-8"))
# #     except:
# #         return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

# #     if isinstance(payload, dict):
# #         payload = [payload]
# #     elif not isinstance(payload, list):
# #         return JsonResponse({"success": False, "message": "Invalid payload format"})


# #     for data in payload:
# #         items = data.get("items", [])

# #         print('this is items: ',items)
    
# #         if not items:
# #             return JsonResponse({"success": False, "message": "No items provided"})

# #         # --- Server-side discount & negative sale policy enforcement (security layer) ---
# #         try:
# #             user_profile = getattr(user, 'userprofile', None)
# #             company = getattr(user_profile, 'company', None)
# #             branch = getattr(user_profile, 'branch', None)
# #             pos_config, _ = get_company_config(
# #                 company.id if company else None,
# #                 branch.id if branch else None
# #             )
# #             pos_cfg = pos_config.get('pos', {})
# #             row_discount_allowed = bool(pos_cfg.get('row_discount_allowed', True))
# #             max_row_disc_pct  = float(pos_cfg.get('max_row_discount_percent', 0) or 0)
# #             max_row_disc_amt  = float(pos_cfg.get('max_row_discount_amount', 0) or 0)
# #             max_total_disc_pct = float(pos_cfg.get('max_total_discount_percent', 0) or 0)
# #             allow_negative_sale = bool(pos_cfg.get('allow_negative_sale', False))

# #             # Validate / sanitize per-row discounts and negative sale
# #             for item in items:
# #                 if not row_discount_allowed:
# #                     item['row_discount_percent'] = 0
# #                     item['row_discount_amount'] = 0
# #                     row_disc_pct = 0
# #                     row_disc_amt = 0
# #                 else:
# #                     qty = float(item.get('qty') or 0)
# #                     rate = float(item.get('rate') or 0)
# #                     gross = qty * rate
# #                     row_disc_pct = float(item.get('row_discount_percent') or 0)
# #                     row_disc_amt = float(item.get('row_discount_amount') or 0)

# #                     # Validate max_row_discount_percent
# #                     if max_row_disc_pct > 0:
# #                         if row_disc_pct > max_row_disc_pct:
# #                             return JsonResponse({
# #                                 "success": False,
# #                                 "message": f"Row discount {row_disc_pct}% exceeds allowed limit of {max_row_disc_pct}%"
# #                             }, status=403)
# #                         if row_disc_amt > 0 and gross > 0:
# #                             effective_pct = (row_disc_amt / gross) * 100
# #                             if effective_pct > max_row_disc_pct:
# #                                 return JsonResponse({
# #                                     "success": False,
# #                                     "message": f"Row discount Rs {row_disc_amt} ({effective_pct:.2f}%) exceeds allowed limit of {max_row_disc_pct}%"
# #                                 }, status=403)

# #                     # Validate max_row_discount_amount
# #                     if max_row_disc_amt > 0:
# #                         if row_disc_amt > max_row_disc_amt:
# #                             return JsonResponse({
# #                                 "success": False,
# #                                 "message": f"Row discount Rs {row_disc_amt} exceeds allowed limit of Rs {max_row_disc_amt}"
# #                             }, status=403)
# #                         if row_disc_pct > 0 and gross > 0:
# #                             effective_amt = (gross * row_disc_pct) / 100
# #                             if effective_amt > max_row_disc_amt:
# #                                 return JsonResponse({
# #                                     "success": False,
# #                                     "message": f"Row discount {row_disc_pct}% (Rs {effective_amt:.2f}) exceeds allowed limit of Rs {max_row_disc_amt}"
# #                                 }, status=403)

# #                 # Negative sale verification
# #                 if not allow_negative_sale and item.get('inv_id'):
# #                     qty = int(item.get('qty') or 0)
# #                     pack_qty = int(item.get('pack_qty') or 1)
# #                     req_base_qty = qty * pack_qty
# #                     old_base_qty = int(item.get('row_old_total_base_qty') or 0) if data.get('bill_no') else 0
# #                     net_qty_deducted = req_base_qty - old_base_qty
# #                     if net_qty_deducted > 0:
# #                         inv_obj = Inventory.objects.filter(inv_id=item.get('inv_id')).first()
# #                         if inv_obj and (inv_obj.bal_qty or 0) < net_qty_deducted:
# #                             return JsonResponse({
# #                                 "success": False,
# #                                 "message": f"Negative sale not allowed. Insufficient stock for '{item.get('prod_name', 'Item')}'. Available: {inv_obj.bal_qty or 0}, Required: {net_qty_deducted}"
# #                             }, status=403)

# #             # Validate total bill discount
# #             if max_total_disc_pct > 0:
# #                 header_disc_pct = float(data.get('header_discount_percent') or 0)
# #                 if header_disc_pct > max_total_disc_pct:
# #                     return JsonResponse({
# #                         "success": False,
# #                         "message": f"Total bill discount {header_disc_pct}% exceeds allowed limit of {max_total_disc_pct}%"
# #                     }, status=403)

# #             # Enforce delivery_charges_allowed: wipe delivery charges if not allowed
# #             if not bool(pos_cfg.get('delivery_charges_allowed', True)):
# #                 data['header_delivery_charges'] = 0

# #             # Enforce tax_charges_allowed: wipe GST if not allowed
# #             if not bool(pos_cfg.get('tax_charges_allowed', True)):
# #                 data['header_gst_percent'] = 0
# #                 data['header_gst_amount'] = 0

# #             # Enforce msc_charges_allowed: wipe misc charges if not allowed
# #             if not bool(pos_cfg.get('msc_charges_allowed', True)):
# #                 data['header_msc_charges'] = 0

# #             # Enforce require_remarks
# #             if bool(pos_cfg.get('require_remarks', False)):
# #                 if not str(data.get('header_remarks') or '').strip():
# #                     return JsonResponse({
# #                         "success": False,
# #                         "message": "Remarks are required before saving the bill."
# #                     }, status=403)

# #         except Exception as policy_err:
# #             # Non-blocking: log but don't crash on config errors
# #             print(f'[save_bill] Policy check error: {policy_err}')
# #         # --- End security enforcement ---

# #         if data.get('bill_no'):
# #             old_bill_no = int(data.get('bill_no'))
# #             old_bill = Invoice.objects.filter(bill_no=old_bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
# #             if not old_bill:
# #                 return JsonResponse({"success": False, "message": "Bill not found"})
# #             old_item = old_bill.filter(is_header = True).first()
# #             fields_will_update = {
# #                 'dateent': old_item.dateent,
# #                 'date':old_item.date,
# #                 'header_edit_count': old_item.header_edit_count + 1,
# #                 'user': old_item.user,
# #                 "bill_no":old_bill_no,
# #             }
# #             update = True
# #             # Reverse stock issued for this invoice BEFORE deleting the rows.
# #             # Restores StockLot.quantity_remaining and Inventory.bal_qty atomically.
# #             try:
# #                 _reverse_voucher_stock(
# #                     company_id=user.userprofile.company.id,
# #                     branch_id=user.userprofile.branch.id,
# #                     voucher_type='SALE',
# #                     voucher_bill_no=old_bill_no,
# #                     block_if_partially_sold=False,
# #                 )
# #                 # Also reverse any sale-return rows that were part of this bill
# #                 _reverse_voucher_stock(
# #                     company_id=user.userprofile.company.id,
# #                     branch_id=user.userprofile.branch.id,
# #                     voucher_type='SALE_RETURN',
# #                     voucher_bill_no=old_bill_no,
# #                     block_if_partially_sold=False,
# #                 )
# #             except Exception as e:
# #                 return JsonResponse({"success": False, "message": str(e)})
# #             old_bill.delete()
            
# #         else:
# #             fields_will_update = {
# #                 'dateent': now_karachi(),
# #                 'date':now_karachi().date() if not data.get('date') else data.get('date'),
# #                 'header_edit_count': 0,
# #                 'user': user,
# #                 "bill_no":get_next_voucher('INV'),
# #             }

# #         system_fields = {
# #             "user": user,
# #             "company": user.userprofile.company,
# #             "branch": user.userprofile.branch,
# #             "posterminal": user.userprofile.terminal,
# #         }
# #         data.pop('local_id',None)
# #         data.pop('items',None)
 
# #         print('this is data: ',data)

# #         sale_date = fields_will_update.get('date')
# #         bill_no = fields_will_update.get('bill_no')

# #         # Build Invoice rows + collect stock data in one O(N) pass
# #         invoices = []
# #         stock_rows = []  # (inv_id, base_qty, row_index)
# #         return_amount=0
# #         positive_amount=0
# #         for index,item in enumerate(items):
# #             first_item = (index == 0)
# #             return_amount += abs(item.get("row_net_total")) if int(item.get("row_net_total")) < 0 else 0
# #             positive_amount += item.get("row_net_total") if int(item.get("row_net_total")) > 0 else 0
# #             if first_item:
# #                 invoices.append(json_to_invoice(item=item, header_fields=data,fields_will_update=fields_will_update,system_fields=system_fields,is_header = True, update = update))
# #             else:
# #                 invoices.append(json_to_invoice(item=item,fields_will_update=fields_will_update,system_fields=system_fields,update=update))

# #             # Collect stock info for every row (including header which also has item)
# #             inv_id = item.get('inv_id')
# #             if inv_id:
# #                 base_qty = Decimal(str(item.get('qty', 0))) * Decimal(str(item.get('pack_qty', 1)))
# #                 stock_rows.append((inv_id, base_qty, index))

# #         Invoice.objects.bulk_create(invoices)

# #         # Fetch created rows to get real PKs (needed for voucher_row_id)
# #         created_invoices = list(Invoice.objects.filter(
# #             bill_no=bill_no,
# #             company=user.userprofile.company,
# #             branch=user.userprofile.branch
# #         ).order_by('id'))

# #         # Issue / receive stock and capture COGS; bulk-update row_net_cost / row_rate_cost
# #         cogs_updates = []
# #         for inv_id, base_qty, row_index in stock_rows:
# #             if base_qty == 0:
# #                 continue
# #             try:
# #                 row_obj = created_invoices[row_index] if row_index < len(created_invoices) else None
# #                 voucher_row_id = row_obj.id if row_obj else None

# #                 if base_qty > 0:
# #                     # Normal sale: stock goes OUT
# #                     total_cogs, per_unit_cogs = STOCK_OUT(
# #                         company_id=user.userprofile.company.id,
# #                         branch_id=user.userprofile.branch.id,
# #                         inventory_item_id=inv_id,
# #                         base_quantity_required=base_qty,
# #                         voucher_date=sale_date,
# #                         voucher_type='SALE',
# #                         voucher_bill_no=bill_no,
# #                         voucher_row_id=voucher_row_id,
# #                         is_update=False,  # reversal already done above
# #                     )
# #                 else:
# #                     # Sale return: stock comes back IN
# #                     _item = Inventory.objects.filter(
# #                         inv_id=inv_id,
# #                         company_id=user.userprofile.company.id,
# #                         branch_id=user.userprofile.branch.id,
# #                     ).values('last_pur_price', 'cost').first() or {}
# #                     return_unit_cost = _item.get('last_pur_price') or _item.get('cost') or Decimal(0)
# #                     abs_qty = abs(base_qty)
# #                     STOCK_IN(
# #                         company_id=user.userprofile.company.id,
# #                         branch_id=user.userprofile.branch.id,
# #                         inventory_item_id=inv_id,
# #                         base_quantity=abs_qty,
# #                         rate_cost_per_unit=return_unit_cost,
# #                         voucher_date=sale_date,
# #                         voucher_type='SALE_RETURN',
# #                         voucher_bill_no=bill_no,
# #                         voucher_row_id=voucher_row_id,
# #                         is_update=False,
# #                     )
# #                     total_cogs = return_unit_cost * abs_qty
# #                     per_unit_cogs = return_unit_cost

# #                 if row_obj:
# #                     row_obj.row_net_cost = total_cogs
# #                     row_obj.row_rate_cost = per_unit_cogs
# #                     cogs_updates.append(row_obj)

# #             except Exception as stock_err:
# #                 print(f'[SALE STOCK] Error for inv_id={inv_id} qty={base_qty}: {stock_err}')

# #         if cogs_updates:
# #             Invoice.objects.bulk_update(cogs_updates, ['row_net_cost', 'row_rate_cost'])




# #         if Decimal(str(data.get('header_total_paid') or "0")) not in [None,0,Decimal("0")] :
# #             # my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else int(data.get('header_payment_mode'))
# #             my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else DEFAULT_MY_BANK_ACCOUNT
# #             v_types = ['CR']
# #             if int(data.get('header_total_paid')) < 0:
# #                 # v_types.append('CP')
# #                 v_types = ['CP']
# #             elif str(data.get('header_payment_mode')).startswith('111'):
# #                 v_types = ["BR"]
# #             # 'CR' if not str(data.get('header_payment_mode')).startswith('111') else 'BR'

# #             lines = [];
# #             return_lines = []
# #             default_cash_client_acc = get_default_account_code('cash_client_acc', company.id if company else None, branch.id if branch else None)

# #             if int(data.get('header_total_paid')) != 0:
# #                 lines.append(GledgLineDTO(
# #                     accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
# #                     head=data.get('head') or "",
# #                     notes= f"INV# {fields_will_update.get('bill_no')}" if int(data.get('header_total_paid'))>0 else f"INV RETURN# {fields_will_update.get('bill_no')}",
# #                     receiptNo = 0,
# #                     chqNo = '0',
# #                     amount = Decimal(abs(Decimal(data.get('header_total_paid')))).quantize(Decimal("0.000")),
# #                     # amount = Decimal(int(positive_amount)).quantize(Decimal("0.000")),
# #                     refAccCode = my_counter_account,
# #                     amtType = "DR" if int(data.get('header_total_paid')) < 0 else 'CR' ,
# #                 ) )


# #             # if return_amount != 0 and False:
# #             #     return_lines.append(
# #             #         GledgLineDTO(
# #             #         accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
# #             #         head=data.get('head') or "",
# #             #         notes= f"INV RETURN# {fields_will_update.get('bill_no')}" ,
# #             #         receiptNo = 0,
# #             #         chqNo = '0',
# #             #         # amount = Decimal(int(data.get('header_total_paid'))).quantize(Decimal("0.000")),
# #             #         amount = Decimal(int(return_amount)).quantize(Decimal("0.000")),
# #             #         refAccCode = my_counter_account,
# #             #         amtType = "DR",
# #             #     ))
            
            
# #             if lines or return_lines:    
# #                 old_positive_vno = 0
# #                 old_gledg = {}
# #                 if update:
# #                     old_gledg = (
# #                         Gledg.objects
# #                         .filter(
# #                             PUR_INV='I',
# #                             INVOICE_ID=fields_will_update.get('bill_no'),
# #                             AMT_TYPE='DR',
# #                             V_TYPE__in=['CP', 'CR', 'BR'],
# #                         )
# #                         .values_list('VNO', 'V_TYPE')
# #                     )


# #                     for vno, v_type in old_gledg:
# #                         if v_type == 'CP':
# #                             old_return_vno = vno

# #                         elif v_type in ['CR', 'BR']:
# #                             old_positive_vno = vno
# #                     print('old_return_vno',old_gledg)
# #                     print('old_return_vno',old_gledg)


# #                 for v_type in v_types:
                    
# #                     created, message, _vno = create_gledg_entries(
# #                         request = request,
# #                         lines=lines,
# #                         # lines=lines if v_type != 'CP' else return_lines,
# #                         date=fields_will_update.get('dateent'),
# #                         v_type=v_type,
# #                         remarks='',
# #                         pur_inv='I',
# #                         update=update if update and len(old_gledg) >= 1 else False,
# #                         # vno_to_update = old_gledg.VNO if update and old_gledg else 0,
# #                         vno_to_update = old_return_vno if update and v_type =='CP' and len(old_gledg) >= 1 else old_positive_vno,
# #                         inv_id=fields_will_update.get('bill_no'),
# #                         called_by_invoices = True,
                        
                        
# #                     ) 
# #                     if not created:
# #                         raise Exception(f"Ledger creation failed: {message}") 

# #     synced = []
# #     header_voucher_no = fields_will_update.get('bill_no')
# #     return JsonResponse({
# #         "success": True,"synced_bills": synced,"header_voucher_no":header_voucher_no

        
# #     })





# # def get_bill(request,bill_no):
# #     user = request.user
# #     if not bill_no:
# #         return JsonResponse({"success": False, "message": "Invalid bill_no"})

# #     try:
# #         bill = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
# #         if not bill:
# #             return JsonResponse({"success": False, "message": "Bill not found"})
# #     except Exception as e:
# #         return JsonResponse({"success": False, "message": str(e)})
# #     # header_row = bill.filter(is_header = True).first()
# #     # items = bill.filter(is_header = False)
# #     try:
# #         item_list = []
# #         for item in bill:
# #             if item.is_header:
# #                 data_list = {
# #                 "bill_no":item.bill_no,
# #                 "branch":str(item.branch),
# #                 "category":str(item.category),
# #                 "company":str(item.company),
# #                 "posterminal" :str(item.posterminal),
# #                 "date":item.date,
# #                 "dateedit":item.dateedit,
# #                 "edit_by":item.edit_by,
# #                 "header_bank_paid":item.header_bank_paid,
# #                 "header_card_last4":item.header_card_last4,
# #                 "header_cash_paid":item.header_cash_paid,
# #                 "header_change_amount":item.header_change_amount,
# #                 "header_delivery_charges":item.header_delivery_charges,
# #                 "header_discount_amount":item.header_discount_amount,
# #                 "header_discount_percent":item.header_discount_percent,
# #                 "header_edit_count":item.header_edit_count,
# #                 "header_gst_amount":item.header_gst_amount,
# #                 "header_gst_percent":item.header_gst_percent,
# #                 "header_item_total":item.header_item_total,
# #                 "header_msc_charges":item.header_msc_charges,
# #                 "header_net_total":item.header_net_total,
# #                 "header_payment_mode":item.header_payment_mode,
# #                 "header_remarks":item.header_remarks,
# #                 "header_total_items":item.header_total_items,
# #                 "header_total_paid" :item.header_total_paid,
# #                 "user" :str(item.user),
# #                 "salesman" :item.salesman,
# #                 "is_header":item.is_header,
# #                 "header_acc_code":item.header_acc_code,
# #             }
# #             item_list.append({
# #                 "inv_id":item.inv_id,
# #                 "pack_qty" :item.pack_qty,
# #                 "packing_mode" :item.packing_mode,
# #                 "prod_name" :item.prod_name,
# #                 "qty" :item.qty,
# #                 "rate" :item.rate,
# #                 "row_discount_amount" :item.row_discount_amount,
# #                 "row_discount_percent" :item.row_discount_percent,
# #                 "row_net_total" :item.row_net_total,
# #                 "row_notes" :item.row_notes,
# #                 "uom" :item.uom,
# #             })
# #         data_list['items']=item_list
# #         # print('data_list======================',item_list)
# #     except Exception as e:
# #         return JsonResponse({"success": False, "message": str(e)})
# #     # print('dtataa===================',data_list)
# #     return JsonResponse({"success": True,"data": data_list,"message":'Successfully Loaded!'})






# # # @api_view(["POST"])
# # @csrf_exempt
# # @transaction.atomic

# # def delete_sale_bill(request,pur_inv,bill_no):
# #     try:
# #         user = request.user
# #         company = user.userprofile.company
# #         branch = user.userprofile.branch
# #         if not user.is_authenticated:
# #             return JsonResponse({"success": False, "message": "User not authenticated"})
# #         if not company:
# #             return JsonResponse({"success": False, "message": "Company not found"})
# #         if not branch:
# #             return JsonResponse({"success": False, "message": "Branch not found"})

# #         if not pur_inv or not bill_no:
# #             return JsonResponse({"success": False, "message": "Pur inv or bill no not found"})

# #         if pur_inv == 'I':
# #             invoice = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
# #             if not invoice:
# #                 return JsonResponse({"success": False, "message": "Invoice not found"})

# #             # Reverse stock before deleting
# #             try:
# #                 _reverse_voucher_stock(
# #                     company_id=user.userprofile.company.id,
# #                     branch_id=user.userprofile.branch.id,
# #                     voucher_type='SALE',
# #                     voucher_bill_no=bill_no,
# #                     block_if_partially_sold=False,
# #                 )
# #                 _reverse_voucher_stock(
# #                     company_id=user.userprofile.company.id,
# #                     branch_id=user.userprofile.branch.id,
# #                     voucher_type='SALE_RETURN',
# #                     voucher_bill_no=bill_no,
# #                     block_if_partially_sold=False,
# #                 )
# #             except Exception as e:
# #                 return JsonResponse({"success": False, "message": str(e)})

# #             gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = invoice.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
# #             if gledg_rows:
# #                 gledg_rows.delete()
                
# #             invoice.delete()

# #         elif pur_inv == 'Q':
# #             quotation = Quotation.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
# #             if not quotation:
# #                 return JsonResponse({"success": False, "message": "Quotation not found"})
# #             quotation.delete()

# #         elif pur_inv == 'P':
# #             purchase = Purchase.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
# #             if not purchase:
# #                 return JsonResponse({"success": False, "message": "Purchase not found"})

# #             # Reverse stock before deleting (blocks if stock partially sold)
# #             try:
# #                 _reverse_voucher_stock(
# #                     company_id=user.userprofile.company.id,
# #                     branch_id=user.userprofile.branch.id,
# #                     voucher_type='PURCHASE',
# #                     voucher_bill_no=bill_no,
# #                     block_if_partially_sold=True,
# #                 )
# #             except ValueError as ve:
# #                 return JsonResponse({"success": False, "message": str(ve)})

# #             gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = purchase.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
# #             if gledg_rows:
# #                 gledg_rows.delete()
                
# #             purchase.delete()
            
# #         return JsonResponse({"success": True,"message":'Successfully Deleted!'})

# #     except Exception as e:
# #         return JsonResponse({"success": False, "message": f"Error deletingd bill: {str(e)}"})





# # @csrf_exempt
# # @require_POST
# # @transaction.atomic
# # def save_bill(request):
# #     user = request.user
# #     fields_will_update = {}
# #     system_fields = {}
# #     update=False
   
# #     try:
# #         data = json.loads(request.body.decode("utf-8"))
# #     except:
# #         return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

# #     items = data.get("items", [])
    
# #     if not items:
# #         return JsonResponse({"success": False, "message": "No items provided"})
    
# #     if data.get('voucher_no'):
# #         old_bill_no = int(data.get('voucher_no'))
# #         old_bill = Invoice.objects.filter(bill_no=old_bill_no ,  user = user)
# #         old_header_row = old_bill.filter(header_row = True).first()
# #         fields_will_update = {
# #             'dateent': old_header_row.dateent,
# #             'header_edit_count': old_header_row.header_edit_count + 1,
# #             'user': old_header_row.user,
# #             "bill_no":old_bill_no,
# #         }
# #         update = True
# #         old_bill.delete()
        
# #     else:
# #         fields_will_update = {
# #             'dateent': now_karachi(),
# #             'header_edit_count': 0,
# #             'user': user,
# #             "bill_no":get_next_voucher('INV'),
# #         }

# #     system_fields = {
# #         "user": user,
# #         "company": user.userprofile.company,
# #         "branch": user.userprofile.branch,
# #         "posterminal": user.userprofile.terminal,
# #     }

# #     # Build Invoices
# #     invoices = []
# #     for index,item in enumerate(items):
# #         first_item = (index == 0)
# #         if first_item:
# #             invoices.append(json_to_invoice(item=item, header_fields=data,fields_will_update=fields_will_update,system_fields=system_fields,is_header = True, update = update))
# #         else:
# #             invoices.append(json_to_invoice(item=item,fields_will_update=fields_will_update,system_fields=system_fields,update=update))
# #     Invoice.objects.bulk_create(invoices)

# #     #gledg
# #     # if data.get('header_total_paid')>0:
# #     #     create_gledg_entry(bill_no,net_total,payment_method,user,1,1)

# #     return JsonResponse({
# #         "success": True,
        
# #     })


# # class Invoice(models.Model):
# #     ver_cntrl = models.CharField(max_length=15)
# #     inv_date = models.DateField(blank=True, null=True)
# #     bill_no = models.IntegerField(blank=True, null=True)
# #     acc_code = models.IntegerField(blank=True, null=True)
# #     inv_id = models.IntegerField(db_comment='Refer to Inventory ID')
# #     pcs_packing = models.CharField(max_length=15)
# #     qty = models.FloatField(blank=True, null=True)
# #     retail_price = models.FloatField(blank=True, null=True)
# #     item_net_amount = models.FloatField(blank=Truae, null=True)
# #     inv_srno = models.IntegerField(blank=True, null=True)
# #     discount = models.FloatField(blank=True, null=True)
# #     disc_percent = models.FloatField()
# #     disc_flat = models.FloatField()
# #     wht = models.FloatField(blank=True, null=True)
# #     gst = models.FloatField(blank=True, null=True)
# #     dateent = models.DateTimeField(blank=True, null=True)
# #     user = models.CharField(max_length=10, blank=True, null=True)
# #     branchid = models.IntegerField(blank=True, null=True)
# #     remarks = models.TextField(blank=True, null=True)
# #     sale_type = models.CharField(max_length=1)
# #     tmp_save = models.CharField(max_length=1)
# #     show_in_sale_rpt = models.CharField(max_length=1)
# #     st_id = models.IntegerField(db_comment='Ref to Store ID')
# #     misc_chrgs = models.FloatField()
# #     supl_inv_no = models.CharField(max_length=35, db_comment='Ref to Supl. Inv# or  Client PO #')
# #     supl_inv_dt = models.DateField(db_comment='Ref to Supl. Inv Date or  Client PO Date')
# #     batch_no = models.CharField(max_length=50)
# #     expire_dt = models.DateField()
# #     item_discount = models.FloatField()
# #     item_disc_per = models.FloatField()
# #     delivery_person = models.CharField(max_length=15)
# #     warranty_print = models.CharField(max_length=200)
# #     our_ref = models.CharField(max_length=25)
# #     our_date = models.DateField()
# #     tran_mode = models.CharField(max_length=10, db_comment='Testing, Checking, Normal')
# #     comp_name = models.CharField(max_length=15)
# #     rate_cost = models.DecimalField(max_digits=23, decimal_places=14)
# #     sales_man = models.CharField(max_length=15)
# #     sale_cost = models.DecimalField(max_digits=23, decimal_places=14)
# #     paid = models.FloatField()
# #     self_trans = models.IntegerField()
# #     builty_no = models.CharField(max_length=15)
# #     builty_dte = models.DateField()
# #     packby = models.CharField(max_length=15)
# #     token_no = models.IntegerField()
# #     table_name = models.CharField(max_length=15)
# #     pur_rate = models.IntegerField()
# #     fake_bill_no = models.CharField(max_length=10)
# #     station = models.CharField(max_length=5)
# #     prod_categ = models.CharField(max_length=25)
# #     pack_qty = models.FloatField()
# #     pack_qty_rate = models.DecimalField(max_digits=10, decimal_places=2)
# #     pctcode = models.CharField(max_length=8)
# #     ispra = models.CharField(max_length=1)
# #     gst_per = models.FloatField()
# #     fbr_inv_no = models.CharField(max_length=30)
# #     fbr_posid = models.IntegerField()
# #     fbr_buyer = models.CharField(max_length=70)
# #     fbr_buyerntn = models.CharField(max_length=9)
# #     fbr_buyercnic = models.CharField(max_length=13)
# #     fbr_buyerphone = models.CharField(max_length=20)

# #     class Meta:
# #         managed = False
# #         db_table = 'invoice'






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







# # @csrf_exempt
# # @require_POST
# # @transaction.atomic
# # def sync_bills(request):
# #     user = request.user
# #     if not user.is_authenticated:
# #         return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)

# #     try:
# #         payload = json.loads(request.body.decode("utf-8"))
# #     except:
# #         return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

# #     if not isinstance(payload, list):
# #         return JsonResponse({"success": False, "message": "Expected list of bills"}, status=400)

# #     synced = []
    
    
  

# #     for bill in payload:
# #         items = bill.get("items", [])
# #         if not items:
# #             continue

# #         offline_local_id = bill.get('local_id',0)
# #         disc_percent = Decimal(bill.get("discountPercent") or 0)
        
# #         if disc_percent > Decimal(9.99):
# #             return JsonResponse({
# #                 "success": False, 
# #                 "message": f"Discount percent too high: {disc_percent} In {offline_local_id}. Max allowed: 9.99"
# #             }, status=400)

# #         delivery_charges = Decimal(bill.get("deliveryCharges") or 0)
# #         received_amount = Decimal(bill.get("receivedAmount") or 0)
# #         remarks = bill.get("remarks", "")
# #         payment_method = bill.get("Payment_method", "cash")

# #         item_total = sum(Decimal(i.get("amount") or 0) for i in items)
# #         disc_flat = (item_total * disc_percent / 100).quantize(Decimal("0.01"))
# #         paymentmethod_detail = bill.get('paymentmethod_detail',"")

# #         net_total = item_total-disc_flat+delivery_charges

# #         #calling helper fucn
# #         bill_no = get_next_bill_no('INV')
# #         create_gledg_entry(bill_no, net_total ,payment_method,user,1,1)

# #         invoices = []
# #         for index,item in enumerate(items):
# #             first_item = (index==0)
# #             invoice = build_invoice(item, bill_no, disc_percent if first_item else 0, disc_flat if first_item else 0,
# #                            delivery_charges if first_item else 0, payment_method, remarks, user.username,
# #                            received_amount if first_item else 0 ,paymentmethod_detail)
# #             invoices.append(invoice)
# #         # invs = [
# #         #     build_invoice(item, bill_no, disc_percent, disc_flat,
# #         #                   delivery_charges, payment, remarks, user.username,
# #         #                   received,paymentmethod_detail)
# #         #     for item in items
# #         # ]
# #         Invoice.objects.bulk_create(invoices)

        
# #         synced.append(bill_no)

# #     return JsonResponse({"success": True, "synced_bills": synced})

# # from django.db import connection
# # from decimal import Decimal
# # from django.http import JsonResponse

# # @require_GET
# # def get_bill(request):
# #     user = request.user
# #     bill_no = request.GET.get("voucher_no")

# #     with connection.cursor() as cursor:

# #         # 1️⃣ Get latest bill if not provided
# #         if not bill_no:
# #             cursor.execute("""
# #                 SELECT bill_no
# #                 FROM invoice
# #                 WHERE user = %s
# #                 ORDER BY bill_no DESC
# #                 LIMIT 1
# #             """, [user])

# #             row = cursor.fetchone()
# #             if not row:
# #                 return JsonResponse({"success": False, "message": "No bills found"})
# #             bill_no = row[0]



# #         # 2️⃣ Fetch everything in ONE query
# #         cursor.execute("""
# #             SELECT
# #                 i.bill_no, i.dateent, i.tran_mode, i.paid,
# #                 i.disc_percent, i.disc_flat, i.misc_chrgs,
# #                 i.remarks,

# #                 i.inv_id, i.qty, i.retail_price,
# #                 i.discount, i.item_net_amount,

# #                 p.prod_name

# #             FROM invoice i
# #             LEFT JOIN inventory p ON p.inv_id = i.inv_id
            
# #             WHERE i.user = %s AND i.bill_no = %s
# #             ORDER BY i.id
# #         """, [ user, bill_no])


# #         # rc.company_name, rc.logo,
# #         #         #         rc.show_header, rc.header_text,
# #         #         rc.show_footer, rc.footer_text
# # # LEFT JOIN ab_receiptconfig rc ON rc.user_id = %s

# #         rows = cursor.fetchall()

# #     if not rows:
# #         return JsonResponse({"success": False, "message": "Bill not found"})

# #     # 3️⃣ Build response (very cheap)
# #     total = Decimal("0")
# #     items = []

# #     for r in rows:
# #         amount = Decimal(str(r[12] or 0))
# #         total += amount

# #         items.append({
# #             "id": r[8],
# #             "description": r[13] or "Unknown Item",
# #             "qty": float(r[9] or 0),
# #             "price": float(r[10] or 0),
# #             "discount": float(r[11] or 0),
# #             "amount": float(amount),
# #         })

# #     h = rows[0]
# #     # print(rows)

# #     remarks = h[7]
# #     if remarks and remarks.startswith("CC#"):
# #         remarks = remarks[8:]

# #     net_total = total - Decimal(str(h[5] or 0)) + Decimal(str(h[6] or 0))
# #     config = get_receipt_config(request.user)
# #     return JsonResponse({
# #         "success": True,
# #         "voucher_no": h[0],
# #         "date": h[1].strftime("%Y-%m-%d %H:%M:%S") if h[1] else None,
# #         "remarks": remarks,
# #         "item_total": float(total),
# #         "net_total": float(net_total),
# #         "discount": float(h[5] or 0),
# #         "discountPercent": float(h[4] or 0),
# #         "delivery_charges": float(h[6] or 0),
# #         "received_amount": float(h[3] or 0),
# #         "payment_mode": h[2],
# #         "items": items,

# #         # "company_name": h[14] or "",
# #         # "logo": request.build_absolute_uri(h[15]) if h[15] else None,
# #         # "show_header": bool(h[16]),
# #         # "header_text": h[17] or "",
# #         # "show_footer": bool(h[18]),
# #         # "footer_text": h[19] or "",
# #         "company_name": config.company_name if config else "",
# #         "logo": request.build_absolute_uri(config.logo.url) if config and config.logo else None,
# #         "show_header": config.show_header if config else False,
# #         "header_text": config.header_text if config else "",
# #         "show_footer": config.show_footer if config else False,
# #         "footer_text": config.footer_text if config else "",
# #     })



# # def qz_sign(request):
# #     msg = request.GET.get("request", "")
# #     key_path = os.path.join("static", "private-key.pem")
# #     key = RSA.import_key(open(key_path, "rb").read())
# #     h = SHA256.new(msg.encode("utf-8"))
# #     signature = pkcs1_15.new(key).sign(h)
# #     return JsonResponse({"signature": base64.b64encode(signature).decode("utf-8")})

# # -----------------------------

# # def json_to_invoice(item={}, header_fields={}, fields_will_update={},system_fields={}):
# #     fields_to_update = {
# #         "bill_no":fields_will_update.get('bill_no'),
# #         "dateent":fields_will_update.get('dateent') or now_karachi(),
# #         "user":fields_will_update.get('user'),
# #         'header_edit_count':fields_will_update.get('edit_count') or 0,
        
# #     }

# #     header_row = {
# #             "is_header":True,

# #             # Header totals
# #             "header_total_items":header_fields.get('header_total_items', 0),
# #             "header_item_total":Decimal(str(header_fields.get('header_item_total', 0))),
# #             "header_discount_percent":Decimal(str(header_fields.get('header_discount_percent', 0))),
# #             "header_discount_amount":Decimal(str(header_fields.get('header_discount_amount', 0))),
# #             "header_delivery_charges":Decimal(str(header_fields.get('header_delivery_charges', 0))),
# #             "header_net_total":Decimal(str(header_fields.get('header_net_total', 0))),
# #             "header_gst_percent":Decimal(str(header_fields.get('header_gst_percent', 0))),
# #             "header_gst_amount":Decimal(str(header_fields.get('header_gst_amount', 0))),
# #             "header_msc_charges":Decimal(str(header_fields.get('header_msc_charges', 0))),

# #             # Payment
# #             "header_payment_mode":header_fields.get('header_payment_mode', 1),
# #             "header_cash_paid":Decimal(str(header_fields.get('header_cash_paid', 0))),
# #             "header_bank_paid":Decimal(str(header_fields.get('header_bank_paid', 0))),
# #             "header_card_last4":header_fields.get('header_card_last4', ''),
# #             "header_total_paid":Decimal(str(header_fields.get('header_total_paid', 0))),
# #             "header_change_amount":Decimal(str(header_fields.get('header_change_amount', 0))),

# #             # Remarks
# #             "header_remarks":header_fields.get('header_remarks', ''),

# #             "salesman":header_fields.get('salesman') or None,
# #         }
    
# #     return Invoice(
# #         **header_row if header_fields else {},
# #         **fields_will_update if fields_will_update else {},
# #         bill_no = bill_no,
# #         inv_id=item.get('inv_id'),
# #         prod_name=item.get('prod_name', ''),
# #         category=item.get('category', ''),
# #         qty=item.get('qty', 0),
# #         rate=item.get('rate', 0),
# #         packing_mode=item.get('packing_mode', 1),
# #         pack_qty=item.get('pack_qty', 0),
# #         row_discount_percent=item.get('row_discount_percent', 0),
# #         row_discount_amount=item.get('row_discount_amount', 0),
# #         row_net_total=item.get('row_net_total', 0),
# #         row_notes=item.get('row_notes', ''),

# #         #header common fields
# #         dateedit = now_karachi() if fields_will_update else None, 
# #         edit_by=user if fields_will_update else None,
        
# #         company=system_fields.get('company') or None,
# #         branch=system_fields.get('branch') or None,
# #         posterminal=system_fields.get('posterminal') or None,
# #     )





# # def create_gledg_entry(
# #         invoice_no,
# #         amount,
# #         payment_method,        # "CASH" or "BANK"
# #         user,
# #         branchid,
# #         station,
# #         prod_categ="Sales",  
# #     ):

# #     CUSTOMER_ACC = 112000001
# #     CASH_ACC     = 110000001
# #     BANK_ACC     = 111000001

 
# #     if payment_method.lower() == "cash":
# #         v_type = "CR"
        
# #         dr_account = CASH_ACC
# #         cr_account = CUSTOMER_ACC
# #         desc1 = f"CR Rcvd against Inv#{invoice_no}"
# #         desc2 = f"CR Rcvd against Inv#{invoice_no}"
# #         paymentmethod = "Cash"

# #     elif payment_method.lower() == "card":
# #         v_type = "BR"
        
# #         dr_account = BANK_ACC
# #         cr_account = CUSTOMER_ACC
# #         desc1 = f"BR Rcvd against Inv#{invoice_no}"
# #         desc2 = f"BR Rcvd against Inv#{invoice_no}"
# #         paymentmethod = "Bank"

# #     else:
# #         raise ValueError("payment_type must be CASH or BANK")

  
# #     vno = get_next_bill_no(v_type)
# #     DEFAULT_CHEQUE_DATE = datetime.date(1900, 1, 1)      
# #     DEFAULT_DRAWN_BRANCH = ""                            
# #     DEFAULT_UPLOAD = "N"
# #     DEFAULT_ISPOSTED = "N"
# #     DEFAULT_INV_YES_NO = "N"
# #     DEFAULT_BANK_RECONCILE = "N"
# #     DEFAULT_ACTUAL_INSTALLMENT = 0
# #     DEFAULT_PUR_INV = "I"

# #     print(now_karachi())
# #     entry_cr = Gledg(
# #         acc_code=cr_account,
# #         ref_acc_code=dr_account,
# #         v_type=v_type,
# #         vno=vno,
# #         date=now_karachi().date(),
# #         desc=desc1,
# #         remarks="",
# #         amount=amount,
# #         amt_type="CR",
# #         chqno="",
# #         # ref_no=invoice_no,
# #         dateent=now_karachi(),
# #         dateedit=None,
# #         user=user,
# #         editby="",
# #         branchid=branchid,
# #         receiptno=None,
# #         shift="1",
# #         cheque_date=DEFAULT_CHEQUE_DATE,
# #         drawn_branch=DEFAULT_DRAWN_BRANCH,
# #         paymentmethod=paymentmethod,
# #         upload=DEFAULT_UPLOAD,
# #         show_in_sale_rpt="N",
# #         isposted=DEFAULT_ISPOSTED,
# #         inv_yes_no=DEFAULT_INV_YES_NO,
# #         bank_reconcile=DEFAULT_BANK_RECONCILE,
# #         actual_installment=DEFAULT_ACTUAL_INSTALLMENT,
# #         pur_inv=DEFAULT_PUR_INV,
# #         station=str(station),
# #         prod_categ=prod_categ,
# #     )
# #     entry_cr.save()

# #     entry_dr = Gledg(
# #         acc_code=dr_account,
# #         ref_acc_code=cr_account,
# #         v_type=v_type,
# #         vno=vno,
# #         date=now_karachi().date(),
# #         desc=desc2,
# #         remarks="",
# #         amount=amount,
# #         amt_type="DR",
# #         chqno="",
# #         # ref_no=invoice_no,
# #         dateent=now_karachi(),
# #         dateedit=None,
# #         user=user,
# #         editby="",
# #         branchid=branchid,
# #         receiptno=None,
# #         shift="1",
# #         cheque_date=DEFAULT_CHEQUE_DATE,
# #         drawn_branch=DEFAULT_DRAWN_BRANCH,
# #         paymentmethod=paymentmethod,
# #         upload=DEFAULT_UPLOAD,
# #         show_in_sale_rpt="N",
# #         isposted=DEFAULT_ISPOSTED,
# #         inv_yes_no=DEFAULT_INV_YES_NO,
# #         bank_reconcile=DEFAULT_BANK_RECONCILE,
# #         actual_installment=DEFAULT_ACTUAL_INSTALLMENT,
# #         pur_inv=DEFAULT_PUR_INV,
# #         station=str(station),
# #         prod_categ=prod_categ,
# #     )
# #     entry_dr.save()

# #     return True






# # @transaction.atomic
# # def get_next_bill_no(type):

# #     # LOCK the row in vchno where type='INV'
# #     vch = (
# #         Vchno.objects
# #         .select_for_update()      # <=== THIS LOCKS THE ROW
# #         .filter(type=type)
# #         .first()
# #     )

# #     # If row doesn't exist, create & lock it
# #     if not vch:
# #         vch = Vchno.objects.create(type=type, vchno=0)

# #     # Get last bill_no from invoice table
# #     last_invoice = Invoice.objects.order_by('-bill_no').first()
# #     last_bill_no = last_invoice.bill_no if last_invoice else 0

# #     current_vchno = vch.vchno or 0

# #     # Compute next bill number (your exact logic)
# #     new_bill_no = max(current_vchno, last_bill_no) + 1

# #     # Update vchno safely (still locked)
# #     vch.vchno = new_bill_no
# #     vch.save(fields_will_update=['vchno'])

# #     return new_bill_no






























# # # -----------------------------
# # def build_invoice(item, bill_no, discount_percent, discount_amount,
# #                   delivery_charges, payment_method, remarks, user,
# #                   received_amount,paymentmethod_detail):

# #     qty = Decimal(item.get("qty") or 1)
# #     rate = Decimal(item.get("rate") or 0)
# #     amount = Decimal(item.get("amount") or (qty * rate))
# #     discount= Decimal(item.get('discount') or 0)
# #     prod_categ = item.get('prod_categ' or '')
# #     return Invoice(
# #         bill_no = bill_no,
# #         inv_id = Decimal(item.get("id", "0")),
# #         qty = qty,
# #         retail_price = rate,
# #         item_net_amount = amount,
# #         prod_categ=prod_categ or 'none',

# #         disc_percent=Decimal(discount_percent),
# #         disc_flat=Decimal(discount_amount),
# #         tran_mode=payment_method,
# #         misc_chrgs=delivery_charges,
# #         remarks=paymentmethod_detail if paymentmethod_detail else remarks,
# #         user=user,
# #         dateent=now_karachi(),
# #         paid=Decimal(received_amount),

# #         acc_code=112000001,
# #         ver_cntrl="",
# #         pcs_packing="",
# #         discount= discount or 0,
# #         gst=Decimal(0),
# #         item_discount=Decimal(0),
# #         item_disc_per=Decimal(0),

# #         inv_date=now_karachi().date(),
# #         supl_inv_dt=datetime.date(1900, 1, 1) ,
# #         supl_inv_no="N/A",
# #         batch_no="N/A",
# #         expe_dt=datetime.date(1900, 1, 1) ,
# #         sale_type="S",
# #         tmp_save="N",
# #         show_in_sale_rpt="Y",
# #         st_id=1,
# #         delivery_person="N/A",
# #         warranty_print="N/A",
# #         our_ref="N/A",
# #         our_date=datetime.date(1900, 1, 1) ,
# #         comp_name="Finish Product",
# #         rate_cost=Decimal(0),
# #         sales_man="N/A",
# #         sale_cost=Decimal(0),

# #         self_trans=0,
# #         builty_no="N/A",
# #         builty_dte=datetime.date(1900, 1, 1) ,
# #         packby="N/A",
# #         token_no=0,
# #         table_name="N/A",
# #         pur_rate=0,
# #         fake_bill_no="N/A",
# #         station="N/A",
        

# #         pack_qty=Decimal(1),
# #         pack_qty_rate=Decimal(0),
# #         pctcode="N/A",
# #         ispra="N",
# #         gst_per=Decimal(0),
# #         fbr_inv_no="N/A",
# #         fbr_posid=0,
# #         fbr_buyer="N/A",
# #         fbr_buyerntn="N/A",
# #         fbr_buyercnic="N/A",
# #         fbr_buyerphone="N/A",
# #     )




# # def get_receipt_config(user):
# #     cache_key = f'receipt_config_{user.id}'
# #     cfg = cache.get(cache_key)
# #     if cfg:
# #         last_update = ReceiptConfigurations.objects.filter(user=user).values_list('updated_at',flat=True).first()
# #         if last_update and last_update == cfg.updated_at:
# #             return cfg
    
# #     cfg = ReceiptConfigurations.objects.filter(user = user).first()
# #     cache.set("receipt_config", cfg, 300)  # 5 minutes
# #     return cfg