



from apps.myglobal.services.helpers import get_user_perms
from django.db import transaction
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
import json
from apps.sale.models import Invoice
from apps.myglobal.services.helpers import get_next_voucher
from django.http import JsonResponse
from apps.sale.services.helpers import json_to_invoice ,now_karachi
from apps.myledger.models import Vchno ,Gledg
from apps.myledger.services.dto import GledgLineDTO
from apps.myledger.services.voucher_utills import create_gledg_entries
from apps.purchase.services.purchase_helpers import handle_inventory_valuation  # kept for fallback
from apps.inventory.services.valuation import STOCK_OUT, _reverse_voucher_stock ,_get_valuation_method
from apps.configuration.selectors import get_company_config, get_default_account_code
from apps.inventory.models import Inventory
from apps.purchase.models import Purchase
from apps.quotation.models import Quotation


DEFAULT_LABOUR_PAYABLE_ACCOUNT = 231000123
DEFAULT_FREIGHT_PAYABLE_ACCOUNT = 231000124
DEFAULT_UNLOAD_PAYABLE_ACCOUNT = 231000125
DEFAULT_MY_CASH_ACCOUNT = 110000001
DEFAULT_MY_BANK_ACCOUNT = 111000001
DEFAULT_MY_CASH_CLIENT_ACCOUNT = 112000001


@csrf_exempt
@require_POST
# @transaction.atomic
def save_bill(request):
    user = request.user
    fields_will_update = {}
    system_fields = {}
    update=False
    
    user_profile = getattr(user, 'userprofile', None)
    company = getattr(user_profile, 'company', None)
    branch = getattr(user_profile, 'branch', None)
   
   
   
    has_return_permission, return_message = get_user_perms(request, "return_sale")
    has_edit_permission, edit_message = get_user_perms(request, "edit_invoice")
    valuation_method = _get_valuation_method(user.userprofile.company.id, user.userprofile.branch.id)
    pos_config, _ = get_company_config(company.id if company else None,branch.id if branch else None)
    # if not has_permission:
    #    return JsonResponse({'success': False, 'message': message}, status=200)
                    
                    
                    
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    if isinstance(payload, dict):
        payload = [payload]
    elif not isinstance(payload, list):
        return JsonResponse({"success": False, "message": "Invalid payload format"})

    
    
    
    gledg_jobs = []
    for data in payload:
        items = data.get("items", [])

        # print('this is items: ',items)
    
        if not items:
            return JsonResponse({"success": False, "message": "No items provided"})

        # --- Server-side discount & negative sale policy enforcement (security layer) ---
        try:
            
            
            pos_cfg = pos_config.get('pos', {})
            row_discount_allowed = bool(pos_cfg.get('row_discount_allowed', True))
            max_row_disc_pct  = float(pos_cfg.get('max_row_discount_percent', 0) or 0)
            max_row_disc_amt  = float(pos_cfg.get('max_row_discount_amount', 0) or 0)
            max_total_disc_pct = float(pos_cfg.get('max_total_discount_percent', 0) or 0)
            allow_negative_sale = bool(pos_cfg.get('allow_negative_sale', False))

            # Validate / sanitize per-row discounts and negative sale
            for item in items:
                if item.get('qty') < 0 and not has_return_permission:
                    return JsonResponse({'success': False, 'message': return_message}, status=200)
                    
                    

                if not row_discount_allowed:
                    item['row_discount_percent'] = 0
                    item['row_discount_amount'] = 0
                    row_disc_pct = 0
                    row_disc_amt = 0
                else:
                    qty = float(item.get('qty') or 0)
                    rate = float(item.get('rate') or 0)
                    gross = qty * rate
                    row_disc_pct = float(item.get('row_discount_percent') or 0)
                    row_disc_amt = float(item.get('row_discount_amount') or 0)

                    # Validate max_row_discount_percent
                    if max_row_disc_pct > 0:
                        if row_disc_pct > max_row_disc_pct:
                            return JsonResponse({
                                "success": False,
                                "message": f"Row discount {row_disc_pct}% exceeds allowed limit of {max_row_disc_pct}%"
                            }, status=403)
                        if row_disc_amt > 0 and gross > 0:
                            effective_pct = (row_disc_amt / gross) * 100
                            if effective_pct > max_row_disc_pct:
                                return JsonResponse({
                                    "success": False,
                                    "message": f"Row discount Rs {row_disc_amt} ({effective_pct:.2f}%) exceeds allowed limit of {max_row_disc_pct}%"
                                }, status=403)

                    # Validate max_row_discount_amount
                    if max_row_disc_amt > 0:
                        if row_disc_amt > max_row_disc_amt:
                            return JsonResponse({
                                "success": False,
                                "message": f"Row discount Rs {row_disc_amt} exceeds allowed limit of Rs {max_row_disc_amt}"
                            }, status=403)
                        if row_disc_pct > 0 and gross > 0:
                            effective_amt = (gross * row_disc_pct) / 100
                            if effective_amt > max_row_disc_amt:
                                return JsonResponse({
                                    "success": False,
                                    "message": f"Row discount {row_disc_pct}% (Rs {effective_amt:.2f}) exceeds allowed limit of Rs {max_row_disc_amt}"
                                }, status=403)

                # Negative sale verification
                if not allow_negative_sale and item.get('inv_id'):
                    qty = int(item.get('qty') or 0)
                    pack_qty = int(item.get('pack_qty') or 1)
                    req_base_qty = qty * pack_qty
                    old_base_qty = int(item.get('row_old_total_base_qty') or 0) if data.get('bill_no') else 0
                    net_qty_deducted = req_base_qty - old_base_qty
                    if net_qty_deducted > 0:
                        inv_obj = Inventory.objects.filter(inv_id=item.get('inv_id')).first()
                        if inv_obj and (inv_obj.bal_qty or 0) < net_qty_deducted:
                            return JsonResponse({
                                "success": False,
                                "message": f"Negative sale not allowed. Insufficient stock for '{item.get('prod_name', 'Item')}'. Available: {inv_obj.bal_qty or 0}, Required: {net_qty_deducted}"
                            }, status=403)

            # Validate total bill discount
            if max_total_disc_pct > 0:
                header_disc_pct = float(data.get('header_discount_percent') or 0)
                if header_disc_pct > max_total_disc_pct:
                    return JsonResponse({
                        "success": False,
                        "message": f"Total bill discount {header_disc_pct}% exceeds allowed limit of {max_total_disc_pct}%"
                    }, status=403)

            # Enforce delivery_charges_allowed: wipe delivery charges if not allowed
            if not bool(pos_cfg.get('delivery_charges_allowed', True)):
                data['header_delivery_charges'] = 0

            # Enforce tax_charges_allowed: wipe GST if not allowed
            if not bool(pos_cfg.get('tax_charges_allowed', True)):
                data['header_gst_percent'] = 0
                data['header_gst_amount'] = 0

            # Enforce msc_charges_allowed: wipe misc charges if not allowed
            if not bool(pos_cfg.get('msc_charges_allowed', True)):
                data['header_msc_charges'] = 0

            # Enforce require_remarks
            if bool(pos_cfg.get('require_remarks', False)):
                if not str(data.get('header_remarks') or '').strip():
                    return JsonResponse({
                        "success": False,
                        "message": "Remarks are required before saving the bill."
                    }, status=403)

        except Exception as policy_err:
            # Non-blocking: log but don't crash on config errors
            print(f'[save_bill] Policy check error: {policy_err}')
        # --- End security enforcement ---
        
        
        # voucher_numbers = []
        # for data in payload:
        #     if not data.get('bill_no'):
        #         with transaction.atomic():
        #             voucher_numbers.append(get_next_voucher('INV'))
        #     else:
        #         voucher_numbers.append(int(data.get('bill_no')))
                
        
        with transaction.atomic():  
            if data.get('bill_no'):
                if not has_edit_permission:
                    return JsonResponse({'success': False, 'message': edit_message}, status=200)

                old_bill_no = int(data.get('bill_no'))
                old_bill = Invoice.objects.filter(bill_no=old_bill_no, company=user.userprofile.company, branch=user.userprofile.branch)
                if not old_bill:
                    return JsonResponse({"success": False, "message": "Bill not found"})
                old_item = old_bill.filter(is_header=True).first()
                fields_will_update = {
                    'dateent': old_item.dateent,
                    'date': old_item.date,
                    'header_edit_count': old_item.header_edit_count + 1,
                    'user': old_item.user,
                    "bill_no": old_bill_no,
                }
                update = True
                # Reverse stock issued for this invoice BEFORE deleting the rows.
                # This restores StockLot.qty_remaining and Inventory.bal_qty atomically.
                try:
                    if not valuation_method == 'LAST_PUR_PRICE':
                        for v_type in ('SALE', 'SALE_RETURN'):
                            _reverse_voucher_stock(
                                company_id=company.id,
                                branch_id=branch.id,
                                voucher_type=v_type,
                                voucher_bill_no=old_bill_no,
                                block_if_partially_sold=False,
                            )
                    old_bill.delete()
                except Exception as e:
                    return JsonResponse({"success": False, "message": str(e)})
                
                
            else:
                fields_will_update = {
                    'dateent': now_karachi(),
                    'date':now_karachi().date() if not data.get('date') else data.get('date'),
                    'header_edit_count': 0,
                    'user': user,
                    "bill_no":get_next_voucher('INV'),
                }

            system_fields = {
                "user": user,
                "company": company,
                "branch": branch,
                "posterminal": user.userprofile.terminal,
            }
            data.pop('local_id',None)
            data.pop('items',None)
    
            sale_date = fields_will_update.get('date')
            bill_no = fields_will_update.get('bill_no')

            # Build Invoice rows + collect stock data in one pass (O(N))
            invoices = []
            stock_rows = []  # (inv_id, base_qty, row_index)
            return_amount = 0
            positive_amount = 0

            for index, item in enumerate(items):
                first_item = (index == 0)
                return_amount += abs(item.get("row_net_total")) if int(item.get("row_net_total")) < 0 else 0
                positive_amount += item.get("row_net_total") if int(item.get("row_net_total")) > 0 else 0
                if first_item:
                    invoices.append(json_to_invoice(item=item, header_fields=data, fields_will_update=fields_will_update, system_fields=system_fields, is_header=True, update=update))
                else:
                    invoices.append(json_to_invoice(item=item, fields_will_update=fields_will_update, system_fields=system_fields, update=update))

                # Collect stock info for every row (including header which also has item)
                inv_id = item.get('inv_id')
                if inv_id:
                    base_qty = Decimal(str(item.get('qty', 0))) * Decimal(str(item.get('pack_qty', 1)))
                    stock_rows.append((inv_id, base_qty, index))

            Invoice.objects.bulk_create(invoices)
            
            
            
            
            
            #print('valuationn method = ', valuation_method)
            
            if valuation_method == 'LAST_PUR_PRICE':
                for inv_id, base_qty, row_index in stock_rows:
                    old_base_qty = int(item.get('row_old_total_base_qty') or 0) if update else 0
                    handle_inventory_valuation(inv_id,base_qty,old_base_qty,called_from='INV',old_base_qty=old_base_qty,update=update)
            
            else:
                
                # Issue stock and capture COGS per row; bulk-update row_net_cost / row_rate_cost
                cogs_updates = []  # list of (inv_obj, total_cogs, per_unit_cogs)
                created_invoices = list(Invoice.objects.filter(
                    bill_no=bill_no,
                    company=user.userprofile.company,
                    branch=user.userprofile.branch
                ).order_by('id'))
                
                for inv_id, base_qty, row_index in stock_rows:
                    if base_qty == 0:
                        continue
                    try:
                        
                        row_obj = created_invoices[row_index]  # <- real row with PK
                        voucher_row_id = row_obj.id 
                        if base_qty > 0:
                            total_cogs, per_unit_cogs = STOCK_OUT(
                                company_id=user.userprofile.company.id,
                                branch_id=user.userprofile.branch.id,
                                inventory_item_id=inv_id,
                                base_quantity_required=base_qty,
                                voucher_date=sale_date,
                                voucher_type='SALE',
                                voucher_bill_no=bill_no,
                                voucher_row_id=voucher_row_id,
                                is_update=False,  # reversal done above before old_bill.delete()
                            )
                        else:
                            total_cogs, per_unit_cogs = STOCK_OUT(
                                company_id=user.userprofile.company.id,
                                branch_id=user.userprofile.branch.id,
                                inventory_item_id=inv_id,
                                base_quantity_required=base_qty,
                                voucher_date=sale_date,
                                voucher_type='SALE_RETURN',
                                voucher_bill_no=bill_no,
                                voucher_row_id=voucher_row_id,
                                is_update=False,  # reversal done above before old_bill.delete()
                            )
                            
                        # Match created row by row_index order (same order as items list)
                        if row_index < len(created_invoices):
                            row_obj = created_invoices[row_index]
                            row_obj.row_net_cost = total_cogs
                            row_obj.row_rate_cost = per_unit_cogs
                            cogs_updates.append(row_obj)
                    except Exception as stock_err:
                        print(f'[STOCK_OUT] Error for inv_id={inv_id}: {stock_err}')

                if cogs_updates:
                    Invoice.objects.bulk_update(cogs_updates, ['row_net_cost', 'row_rate_cost'])


        response = JsonResponse({"success": True, "header_voucher_no": bill_no})


        
        gledg_jobs.append({
            'data_copy': {
                'header_total_paid': data.get('header_total_paid'),
                'header_payment_mode': data.get('header_payment_mode'),
                'header_acc_code': data.get('header_acc_code'),
                'head': data.get('head'),
            },
            'bill_no': bill_no,
            'dateent': fields_will_update.get('dateent'),
            'update': update,
            'company_id': company.id,
            'branch_id': branch.id,
        })
        
        
        def _do_gledg():
            
            
            if Decimal(str(data.get('header_total_paid') or "0")) not in [None,0,Decimal("0")] :
                # my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else int(data.get('header_payment_mode'))
                my_counter_account = DEFAULT_MY_CASH_ACCOUNT if not str(data.get('header_payment_mode')).startswith('111') else DEFAULT_MY_BANK_ACCOUNT
                v_types = ['CR']
                if int(data.get('header_total_paid')) < 0:
                    # v_types.append('CP')
                    v_types = ['CP']
                elif str(data.get('header_payment_mode')).startswith('111'):
                    v_types = ["BR"]
                # 'CR' if not str(data.get('header_payment_mode')).startswith('111') else 'BR'

                lines = [];
                return_lines = []
                default_cash_client_acc = get_default_account_code('cash_client_acc', company.id if company else None, branch.id if branch else None)

                if int(data.get('header_total_paid')) != 0:
                    lines.append(GledgLineDTO(
                        accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
                        head=data.get('head') or "",
                        notes= f"INV# {fields_will_update.get('bill_no')}" if int(data.get('header_total_paid'))>0 else f"INV RETURN# {fields_will_update.get('bill_no')}",
                        receiptNo = 0,
                        chqNo = '0',
                        amount = Decimal(abs(Decimal(data.get('header_total_paid')))).quantize(Decimal("0.000")),
                        # amount = Decimal(int(positive_amount)).quantize(Decimal("0.000")),
                        refAccCode = my_counter_account,
                        amtType = "DR" if int(data.get('header_total_paid')) < 0 else 'CR' ,
                    ) )


                # if return_amount != 0 and False:
                #     return_lines.append(
                #         GledgLineDTO(
                #         accCode=int(data.get('header_acc_code') or 0) if data.get('header_acc_code') else default_cash_client_acc,
                #         head=data.get('head') or "",
                #         notes= f"INV RETURN# {fields_will_update.get('bill_no')}" ,
                #         receiptNo = 0,
                #         chqNo = '0',
                #         # amount = Decimal(int(data.get('header_total_paid'))).quantize(Decimal("0.000")),
                #         amount = Decimal(int(return_amount)).quantize(Decimal("0.000")),
                #         refAccCode = my_counter_account,
                #         amtType = "DR",
                #     ))
                
                
                if lines or return_lines:    
                    old_positive_vno = 0
                    old_gledg = {}
                    if update:
                        old_gledg = (
                            Gledg.objects
                            .filter(
                                PUR_INV='I',
                                INVOICE_ID=fields_will_update.get('bill_no'),
                                AMT_TYPE='DR',
                                V_TYPE__in=['CP', 'CR', 'BR'],
                            )
                            .values_list('VNO', 'V_TYPE')
                        )


                        for vno, v_type in old_gledg:
                            if v_type == 'CP':
                                old_return_vno = vno

                            elif v_type in ['CR', 'BR']:
                                old_positive_vno = vno
                        # print('old_return_vno',old_gledg)
                        # print('old_return_vno',old_gledg)


                    for v_type in v_types:
                        
                        created, message, _vno = create_gledg_entries(
                            request = request,
                            lines=lines,
                            # lines=lines if v_type != 'CP' else return_lines,
                            date=fields_will_update.get('dateent'),
                            v_type=v_type,
                            remarks='',
                            pur_inv='I',
                            update=update if update and len(old_gledg) >= 1 else False,
                            # vno_to_update = old_gledg.VNO if update and old_gledg else 0,
                            vno_to_update = old_return_vno if update and v_type =='CP' and len(old_gledg) >= 1 else old_positive_vno,
                            inv_id=fields_will_update.get('bill_no'),
                            called_by_invoices = True,
                            
                            
                        ) 
                        if not created:
                            raise Exception(f"Ledger creation failed: {message}") 
        
        
        
        transaction.on_commit(_do_gledg)


    # synced = []
    # header_voucher_no = fields_will_update.get('bill_no')
    return response

    # return JsonResponse({
    #     "success": True,"synced_bills": synced,"header_voucher_no":header_voucher_no

        
    # })





def get_bill(request,bill_no):
    
    
    has_permission, message = get_user_perms(request, "edit_invoice")
    if not has_permission:
        return JsonResponse({'success': False, 'message': message}, status=200)

    
    user = request.user
    if not bill_no:
        return JsonResponse({"success": False, "message": "Invalid bill_no"})

    try:
        bill = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
        if not bill:
            return JsonResponse({"success": False, "message": "Bill not found"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})
    # header_row = bill.filter(is_header = True).first()
    # items = bill.filter(is_header = False)
    try:
        item_list = []
        for item in bill:
            if item.is_header:
                data_list = {
                "bill_no":item.bill_no,
                "branch":str(item.branch),
                "category":str(item.category),
                "company":str(item.company),
                "posterminal" :str(item.posterminal),
                "date":item.date,
                "dateedit":item.dateedit,
                "edit_by":item.edit_by,
                "header_bank_paid":item.header_bank_paid,
                "header_card_last4":item.header_card_last4,
                "header_cash_paid":item.header_cash_paid,
                "header_change_amount":item.header_change_amount,
                "header_delivery_charges":item.header_delivery_charges,
                "header_discount_amount":item.header_discount_amount,
                "header_discount_percent":item.header_discount_percent,
                "header_edit_count":item.header_edit_count,
                "header_gst_amount":item.header_gst_amount,
                "header_gst_percent":item.header_gst_percent,
                "header_item_total":item.header_item_total,
                "header_msc_charges":item.header_msc_charges,
                "header_net_total":item.header_net_total,
                "header_payment_mode":item.header_payment_mode,
                "header_remarks":item.header_remarks,
                "header_total_items":item.header_total_items,
                "header_total_paid" :item.header_total_paid,
                "user" :str(item.user),
                "salesman" :item.salesman,
                "is_header":item.is_header,
                "header_acc_code":item.header_acc_code,
            }
            item_list.append({
                "inv_id":item.inv_id,
                "pack_qty" :item.pack_qty,
                "packing_mode" :item.packing_mode,
                "prod_name" :item.prod_name,
                "qty" :item.qty,
                "rate" :item.rate,
                "row_discount_amount" :item.row_discount_amount,
                "row_discount_percent" :item.row_discount_percent,
                "row_net_total" :item.row_net_total,
                "row_notes" :item.row_notes,
                "uom" :item.uom,
            })
        data_list['items']=item_list
        # print('data_list======================',item_list)
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})
    # print('dtataa===================',data_list)
    return JsonResponse({"success": True,"data": data_list,"message":'Successfully Loaded!'})






# @api_view(["POST"])
@csrf_exempt
@transaction.atomic

def delete_sale_bill(request,pur_inv,bill_no):
    try:
        user = request.user
        company = user.userprofile.company
        branch = user.userprofile.branch
        if not user.is_authenticated:
            return JsonResponse({"success": False, "message": "User not authenticated"})
        if not company:
            return JsonResponse({"success": False, "message": "Company not found"})
        if not branch:
            return JsonResponse({"success": False, "message": "Branch not found"})

        if not pur_inv or not bill_no:
            return JsonResponse({"success": False, "message": "Pur inv or bill no not found"})

        if pur_inv == 'I':
            invoice = Invoice.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
            if not invoice:
                return JsonResponse({"success": False, "message": "Invoice not found"})

            
            try:
                
                for v_type in ('SALE', 'SALE_RETURN'):
                    _reverse_voucher_stock(
                        company_id=user.userprofile.company.id,
                        branch_id=user.userprofile.branch.id,
                        voucher_type=v_type,
                        voucher_bill_no=bill_no,
                        block_if_partially_sold=False,
                    )
                
            
            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)})
            
            
            
            gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = invoice.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
            if gledg_rows:
                gledg_rows.delete()
                
            invoice.delete()

        elif pur_inv == 'Q':
            quotation = Quotation.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
            if not quotation:
                return JsonResponse({"success": False, "message": "Quotation not found"})
            
            
            quotation.delete()

        elif pur_inv == 'P':
            purchase = Purchase.objects.filter(bill_no=bill_no,company = user.userprofile.company,branch = user.userprofile.branch)
            if not purchase:
                return JsonResponse({"success": False, "message": "Purchase not found"})

            gledg_rows = Gledg.objects.filter(PUR_INV = pur_inv,INVOICE_ID = purchase.first().bill_no,COMPANY = user.userprofile.company,BRANCH = user.userprofile.branch)
            
            
            try:
                
                for v_type in ('PURCHASE','PURCHASE_RETURN'):
                    _reverse_voucher_stock(
                        company_id=user.userprofile.company.id,
                        branch_id=user.userprofile.branch.id,
                        voucher_type=v_type,
                        voucher_bill_no=bill_no,
                        block_if_partially_sold=True,
                    )
                
                
            
            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)})
            
            
            if gledg_rows:
                gledg_rows.delete()
                
            purchase.delete()
            
        return JsonResponse({"success": True,"message":'Successfully Deleted!'})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error deletingd bill: {str(e)}"})
    
    
    