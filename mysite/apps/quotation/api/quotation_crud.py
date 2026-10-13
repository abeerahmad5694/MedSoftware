
from django.shortcuts import render
from django.db import transaction

# from django.db.models import Q
from django.views.decorators.http import require_GET, require_POST
# 
# from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
# from django.utils import timezone

# import datetime
# import pytz #type:ignore
# import os
# import base64
# from django.db.models import Sum 
# from django.forms.models import model_to_dict
# from django.shortcuts import redirect
# from Crypto.PublicKey import RSA #type:ignore
# from Crypto.Signature import pkcs1_15 #type:ignore
# from Crypto.Hash import SHA256 #type:ignore

# from apps.inventory.models import Product
# from .models import Invoice,Vchno ,BarcodConfig , Features

# from apps.reusable_app.global_search_utils import global_search
# from apps.admin_settings.models import ReceiptConfigurations


from decimal import Decimal
import json
from apps.sale.models import Invoice
from apps.myglobal.services.helpers import get_next_voucher
from django.http import JsonResponse
from apps.sale.services.helpers import json_to_invoice ,now_karachi
# from apps.sale.services.
from django.forms.models import model_to_dict
from apps.quotation.models import Quotation


model_name = Quotation
@csrf_exempt
@require_POST
@transaction.atomic
def save_bill(request):
    user = request.user
    fields_will_update = {}
    system_fields = {}
    update=False
   
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    if isinstance(payload, dict):
        payload = [payload]
    elif not isinstance(payload, list):
        return JsonResponse({"success": False, "message": "Invalid payload format"})


    # print('palyod=============',payload)
    for data in payload:
        # print('data====' , data)
        items = data.get("items", [])
        
        if not items:
            return JsonResponse({"success": False, "message": "No items provided"})
        
        print('data==========================',data.get('bill_no'))
        if data.get('bill_no'):
            print('dataold bill================',data.get('bill_no'),data)
            old_bill_no = int(data.get('bill_no'))
            old_bill = model_name.objects.filter(bill_no=old_bill_no ,  user = user)
            old_item = old_bill.filter(is_header = True).first()
            fields_will_update = {
                'dateent': old_item.dateent,
                'date':old_item.date,
                'header_edit_count': old_item.header_edit_count + 1,
                'user': old_item.user,
                "bill_no":old_bill_no,
            }
            update = True
            old_bill.delete()
            
        else:
            fields_will_update = {
                'dateent': now_karachi(),
                'date':now_karachi().date(),
                'header_edit_count': 0,
                'user': user,
                "bill_no":get_next_voucher('QOT'),
            }

        system_fields = {
            "user": user,
            "company": user.userprofile.company,
            "branch": user.userprofile.branch,
            "posterminal": user.userprofile.terminal,
        }
        data.pop('local_id',None)
        data.pop('items',None)

        # Build Invoices
        invoices = []
        for index,item in enumerate(items):
            first_item = (index == 0)
            if first_item:
                invoices.append(json_to_invoice(item=item, header_fields=data,fields_will_update=fields_will_update,system_fields=system_fields,is_header = True, update = update))
            else:
                invoices.append(json_to_invoice(item=item,fields_will_update=fields_will_update,system_fields=system_fields,update=update))
        model_name.objects.bulk_create(invoices)


    synced = []
    return JsonResponse({
        "success": True,"synced_bills": synced , 'header_voucher_no':fields_will_update.get('bill_no')
        
    })





def get_bill(request,bill_no):
    user = request.user
    if not bill_no:
        return JsonResponse({"success": False, "message": "Invalid bill_no"})

    try:
        bill = model_name.objects.filter(bill_no=bill_no , user = user)
        # print('bill=============================',bill)
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



