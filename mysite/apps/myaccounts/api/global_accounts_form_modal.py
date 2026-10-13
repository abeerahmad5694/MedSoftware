from apps.myaccounts.api import chart_of_accounts_api
from django.http import JsonResponse
from apps.myaccounts.models import Accounts
from django.utils import timezone
from apps.myaccounts.services.accounts_utills import generate_next_account_code ,get_class_field_and_account_type_by_starting_code
import json
from django.db import transaction
from django.core.cache import cache
today = timezone.now()
from apps.myaccounts.constants import *
from apps.myledger.services.fixed_filters import get_fixed_filters
from apps.myledger.services.helpers import get_user_perms

def get_account(request,acc_code):
    try:
        acc_code = int(acc_code)
    except (ValueError, TypeError):
        return JsonResponse({'success':False,'error': 'Invalid account code'}, status=400)
    try:
        # account = Accounts.objects.filter(ACC_CODE=acc_code).first()
        account = Accounts.objects.only(
            'ACC_CODE',
            'ACC_NAME',
            'SALESMAN',
            'MOBILE_NO',
            'PHONE_OFF',
            'EMAIL_ADDRESS',
            'ADDRESS',
            'CITY',
            'COUNTRY',
            'OPENING_BALANCE',
            'BALANCE_TYPE',
            'CREDIT_LIMIT',
            'NTN_NO',
            'STN_NO',
            'REMARKS',
            'PASSWORD',
            # 'LOCKED',
        ).filter(ACC_CODE=acc_code).first()
        if not account:
            return JsonResponse({'success':False,'message': 'Account not found',"update_or_create":'create'}, status=200)
        data = {
            'ACC_CODE': account.ACC_CODE,
            'ACC_NAME': account.ACC_NAME,
            'SALESMAN': account.SALESMAN,
            'MOBILE_NO': account.MOBILE_NO,
            'PHONE_OFF': account.PHONE_OFF,
            'EMAIL_ADDRESS': account.EMAIL_ADDRESS,
            'ADDRESS': account.ADDRESS,
            'CITY': account.CITY,
            'COUNTRY': account.COUNTRY,
            'OPENING_BALANCE': account.OPENING_BALANCE,
            'BALANCE_TYPE': account.BALANCE_TYPE,
            'CREDIT_LIMIT': account.CREDIT_LIMIT,
            'NTN_NO': account.NTN_NO,
            'STN_NO': account.STN_NO,
            'REMARKS': account.REMARKS,
            'PASSWORD': account.PASSWORD,
            # 'LOCKED': account.LOCKED,
           
        }
        return JsonResponse({'success':True,'message':'Ready to update account', "update_or_create":'update','data':data},status=200)
    except Exception as e:
        print('problem',e);
        return JsonResponse({'success':False,'error': str(e)}, status=500)  



def save_update_account(request, acc_code):
    fixed = get_fixed_filters(request)
    can_create_account,create_account_message = get_user_perms(request, "create_accounts")
    can_edit_account,edit_account_message = get_user_perms(request, "edit_accounts")
    # if not can_create_account:
    #     return JsonResponse({'success': False, 'message': create_account_message}, status=200)
    
    try:
        acc_code = int(acc_code)

        existing_account = Accounts.objects.filter(
            ACC_CODE=acc_code
        ).first()

        if existing_account:
            # -------------------------
            # UPDATE
            # -------------------------
            if not can_edit_account:
                return JsonResponse(
                    {
                        'success': False,
                        'message': edit_account_message
                    },
                    status=200
                )
        else:
            # -------------------------
            # CREATE
            # -------------------------
            if not can_create_account:
                return JsonResponse(
                    {
                        'success': False,
                        'message': create_account_message
                    },
                    status=200
                )



    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid account code'}, status=400)

    try:
        # Helper functions to sanitize inputs
        def to_float(val):
            try: return float(val) if val else 0.0
            except: return 0.0
            
        def to_int(val):
            try: return int(val) if val else 0
            except: return 0

        def to_bool(val):
            return str(val).lower() == 'true'

        now = timezone.now()
        # print(request.POST,'request.POST');
        defaults = {
            'ACC_NAME': request.POST.get('ACC_NAME', ''),
            'SALESMAN': request.POST.get('SALESMAN', ''),
            'MOBILE_NO': request.POST.get('MOBILE_NO', ''),
            'PHONE_OFF': request.POST.get('PHONE_OFF', ''),
            'EMAIL_ADDRESS': request.POST.get('EMAIL_ADDRESS', ''),
            'ADDRESS': request.POST.get('ADDRESS', ''),
            'CITY': request.POST.get('CITY', ''),
            'COUNTRY': request.POST.get('COUNTRY', ''),
            'OPENING_BALANCE': to_float(request.POST.get('OPENING_BALANCE')),
            'BALANCE_TYPE': request.POST.get('BALANCE_TYPE', ''),
            'CREDIT_LIMIT': to_int(request.POST.get('CREDIT_LIMIT')),
            'NTN_NO': request.POST.get('NTN_NO', ''),
            'STN_NO': request.POST.get('STN_NO', ''),
            'REMARKS': request.POST.get('REMARKS', ''),
            'PASSWORD': request.POST.get('PASSWORD', ''),
            # 'LOCKED': to_bool(request.POST.get('LOCKED')),
            'DATEEDIT': now,
            'ENABLE': 'Y',
        }

        with transaction.atomic():
            account, created = Accounts.objects.update_or_create(
                ACC_CODE=acc_code,
                defaults=defaults
            )

            if created:
                account.USER = request.user.username if request.user.is_authenticated else 'system'
                account.DATEENT = now
                level = int(request.POST.get('LEVEL', 0))

                class_field_acc_type = get_class_field_and_account_type_by_starting_code(
                    str(acc_code),
                    level
                )
                
                account.CLASS_FIELD =class_field_acc_type['class_field']
                account.LEVEL = level
                account.TYPE = class_field_acc_type['account_type']
                account.COMPANY = fixed['COMPANY']
                account.BRANCH = fixed['BRANCH']
                account.POSTERMINAL = fixed['POSTERMINAL']
                # account.DEPT = fixed['department']
                account.save(update_fields=['USER', 'DATEENT','TYPE','LEVEL','CLASS_FIELD','COMPANY','BRANCH','POSTERMINAL'])
                # account.save(update_fields=['TYPE','LEVEL','CLASS_FIELD'])
                if str(acc_code).startswith('111'):
                    cache.delete('bank_accounts_list')
                return JsonResponse({'success': 'Account created successfully'})
            else:

                # if not can_edit_account:
                #     return JsonResponse({'success': False, 'message': edit_account_message}, status=200)

                account.EDITBY = request.user.username if request.user.is_authenticated else 'system'
                account.save(update_fields=['EDITBY'])    
                # account.save()
                if not account.LEVEL or not account.CLASS_FIELD or not account.TYPE:
                    level = int(request.POST.get('LEVEL', 0))

                    class_field_acc_type = get_class_field_and_account_type_by_starting_code(
                        str(acc_code),
                        level
                    )
                    
                    account.CLASS_FIELD = class_field_acc_type['class_field']
                    account.LEVEL = level
                    account.TYPE = class_field_acc_type['account_type']
                    # account.save(update_fields=['USER', 'DATEENT','TYPE','LEVEL','CLASS_FIELD'])
                    account.save(update_fields=['TYPE','LEVEL','CLASS_FIELD'])
                
                return JsonResponse({'success': 'Account updated successfully'})

    except Exception as e:
        print(f"Save error: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def get_next_account_code(request):
    data = json.loads(request.body)
    parent_acc_code = data.get('parent_acc_code')
    level = data.get('level')
    print('level',level,parent_acc_code)
    next_acc_code = generate_next_account_code(parent_acc_code,level)
    
    if not next_acc_code:
        return JsonResponse({'success':False,'message':'There is some thing wrong while generating Code!'})
    
    return JsonResponse({'success':True,'message':'Code generated successfully!','next_acc_code': next_acc_code})    