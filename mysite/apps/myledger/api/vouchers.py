# pyrefly: ignore [missing-import]
from apps.myledger.services.voucher_utills import create_gledg_entries , delete_gledg_entries ,get_gledg_entries
# pyrefly: ignore [missing-import]
from apps.myledger.services.dto import GledgLineDTO
from django.http import JsonResponse
from decimal import Decimal
# pyrefly: ignore [missing-import]
from apps.myledger.selectors.db_queries import get_all_bank_accounts
import json
# pyrefly: ignore [missing-import]
from apps.myledger.services.helpers import get_user_perms


def get_all_banks(request):
    banks = list(get_all_bank_accounts())
    if not banks:
        return JsonResponse({'success':False, 'error' : 'No banks found'})
    return JsonResponse({'success':True, 'data' : banks})
    



def save_dynamic_voucher(request):
    if request.method == 'POST':

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        v_type = data.get("voucherType")
        if v_type == 'JV':
            dr_ac_code = data.get("acc_from_id")  # Debit account code from frontend
            acc_head_dr = data.get('acc_head_dr')
            acc_head_cr = data.get('acc_head_cr')
            cr_ac_code = data.get("acc_to_id")    # Credit account code from frontend
            amount = data.get("amount")
            
            if not dr_ac_code:
                return JsonResponse({'success': False, 'error': 'Debit Account is required'}, status=400)
            if not cr_ac_code:
                return JsonResponse({'success': False, 'error': 'Credit Account is required'}, status=400)
            try:
                dec_amount = Decimal(str(amount))
                if dec_amount <= 0:
                    raise ValueError
            except (ValueError, TypeError, KeyError):
                return JsonResponse({'success': False, 'error': 'Amount must be a valid number greater than zero'}, status=400)
            
            receipt_no = data.get("receiptno") or data.get("receiptNo") or 0
            chq_no = data.get("chqno") or data.get("chqNo") or ""
            notes = data.get("notes") or ""
            
            lines = [
                GledgLineDTO(
                    accCode=int(dr_ac_code),
                    amount=dec_amount,
                    refAccCode=int(cr_ac_code),
                    receiptNo=int(receipt_no) if receipt_no else 0,
                    chqNo=str(chq_no),
                    notes=notes,
                    head=acc_head_dr,
                    amtType="DR",
                ),
                GledgLineDTO(
                    accCode=int(cr_ac_code),
                    amount=dec_amount,
                    refAccCode=int(dr_ac_code),
                    receiptNo=int(receipt_no) if receipt_no else 0,
                    chqNo=str(chq_no),
                    notes=notes,
                    head =acc_head_cr,
                    amtType="CR",
                )
            ]
        else:
            lines = [GledgLineDTO(**line) for line in data.get("listOfVoucherLines", [])]
            
        date = data.get("date")
        remarks = data.get("remarks")
        update = data.get("update")
        vno_to_update = data.get("vno")
        transaction_type = data.get("transactionType")
        
        can_create_voucher,create_voucher_message = get_user_perms(request, "create_vouchers")
        can_edit_voucher,edit_voucher_message = get_user_perms(request, "edit_vouchers")

        if update and not can_edit_voucher:
            # is_allocated = Gledg.objects.filter(vno = )
            return JsonResponse({'success': False, 'message': edit_voucher_message}, status=200)

        if not update and not can_create_voucher:
            return JsonResponse({'success': False, 'message': create_voucher_message}, status=200)

        created, message, saved_vno = create_gledg_entries(
            request = request,
            lines=lines,
            date=date,
            v_type=v_type,
            remarks=remarks,
            pur_inv='V',
            update=update,
            vno_to_update=vno_to_update,
            inv_id='0',
            transaction_type=transaction_type,
        )
        if created:
            print('message',message)
            return JsonResponse({
                'success': True,
                'message': message,
                'vno': saved_vno,
            })
        return JsonResponse({'success': False, 'message': message}, status=200)
        
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    


def delete_dynamic_voucher(request):
    if request.method == 'DELETE':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        
        can_delete, delete_message = get_user_perms(request, "delete_vouchers")
        if not can_delete:
            return JsonResponse({'success': False, 'message': delete_message}, status=200)

        v_type = data.get("voucherType")
        vno = data.get("vno")
        res = delete_gledg_entries(
            v_type=v_type,
            vno=vno,
        )
        return JsonResponse(res)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)



def get_dynamic_voucher(request,vno,v_type):
    if request.method == 'GET':
        data = get_gledg_entries(
            data={
                'V_TYPE':v_type if v_type != 'ADJ' else 'JV',
                'VNO':vno,
            }
        )
        return JsonResponse({'success':True, 'data' : list(data)})