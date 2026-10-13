

# @csrf_exempt
# @require_POST
# @transaction.atomic
# def save_bill(request):
#     user = request.user
#     fields_will_update = {}
#     system_fields = {}
#     update=False
   
#     try:
#         data = json.loads(request.body.decode("utf-8"))
#     except:
#         return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

#     items = data.get("items", [])
    
#     if not items:
#         return JsonResponse({"success": False, "message": "No items provided"})
    
#     if data.get('voucher_no'):
#         old_bill_no = int(data.get('voucher_no'))
#         old_bill = Invoice.objects.filter(bill_no=old_bill_no ,  user = user)
#         old_header_row = old_bill.filter(header_row = True).first()
#         fields_will_update = {
#             'dateent': old_header_row.dateent,
#             'header_edit_count': old_header_row.header_edit_count + 1,
#             'user': old_header_row.user,
#             "bill_no":old_bill_no,
#         }
#         update = True
#         old_bill.delete()
        
#     else:
#         fields_will_update = {
#             'dateent': now_karachi(),
#             'header_edit_count': 0,
#             'user': user,
#             "bill_no":get_next_voucher('INV'),
#         }

#     system_fields = {
#         "user": user,
#         "company": user.userprofile.company,
#         "branch": user.userprofile.branch,
#         "posterminal": user.userprofile.terminal,
#     }

#     # Build Invoices
#     invoices = []
#     for index,item in enumerate(items):
#         first_item = (index == 0)
#         if first_item:
#             invoices.append(json_to_invoice(item=item, header_fields=data,fields_will_update=fields_will_update,system_fields=system_fields,is_header = True, update = update))
#         else:
#             invoices.append(json_to_invoice(item=item,fields_will_update=fields_will_update,system_fields=system_fields,update=update))
#     Invoice.objects.bulk_create(invoices)

#     #gledg
#     # if data.get('header_total_paid')>0:
#     #     create_gledg_entry(bill_no,net_total,payment_method,user,1,1)

#     return JsonResponse({
#         "success": True,
        
#     })

