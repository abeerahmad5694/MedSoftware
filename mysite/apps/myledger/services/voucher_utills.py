from django.core.checks import database
from apps.myledger.models import Gledg 
from django.db import transaction
from django.utils import timezone
from apps.myledger.services.validators import validate_gledg_amount
from django.db import connection
from apps.myledger.models import Vchno
from apps.myledger.constants import SRNO_MAPPING , DETAIL_LEVEL , DEFAULT_ACCOUNTS
from apps.myledger.services.helpers import get_server_datetime, get_next_voucher, get_srno
from decimal import Decimal
from collections import defaultdict
from apps.myledger.services.fixed_filters import get_fixed_filters
from apps.configuration.models import Company, Branch, POSTerminal



# lines = [
#             GledgLineDTO(
#                 accCode=int(data.get('header_acc_code') or 0),
#                 head=data.get('head') or "",
#                 notes= f"PUR# {fields_will_update.get('bill_no')}",
#                 receiptNo = 0,
#                 chqNo = '0',
#                 amount = Decimal(int(data.get('header_total_paid'))).quantize(Decimal("0.000")),
#                 refAccCode = 231000001,
#                 amtType = "DR",

#             ),
#         ]
            
#         created,message = create_gledg_entries(
#             request = request,
#             lines=lines,
#             date=fields_will_update.get('dateent'),
#             v_type="CP",
#             remarks='',
#             pur_inv='P',
#             update=update,
#             vno_to_update=0,
#             inv_id=fields_will_update.get('bill_no'),
            
#         )



def create_gledg_entries(
    *,
    request = None,
    lines,
    date=None,
    v_type,
    remarks="",
    inv_id=0,
    pur_inv="V",
    update=False,
    vno_to_update=None,
    transaction_type=None,
    called_by_invoices = False
 ):  

    
    gledg_to_update = {}
    # user_perms = request.user.userprofile.get_permissions()
    


    if update and not vno_to_update:
        return False, "Voucher not found" ,0
    
        
    # if update and not user_perms.filter(code="edit_payments").exists():
    #     return False, "You don't have permission to edit this voucher"


    # if not update and not user_perms.filter(code="create_payments").exists():
    #     return False, "You don't have permission to create this voucher"


    if update:
        gledg_queryset = Gledg.objects.filter(
        V_TYPE=v_type,
        VNO=vno_to_update
        )

        gledg_to_update = gledg_queryset.values(
            'VNO',
            'USER',
            'DATEENT',
            'COMPANY',
            'BRANCH',
            'INVOICE_ID',
            'POSTERMINAL',
        ).first() or {}
        print('Gledg to Update ',gledg_to_update.get("INVOICE_ID"))
        if not called_by_invoices and gledg_to_update.get("INVOICE_ID") and gledg_to_update.get("INVOICE_ID")>0:
            return False, f'This Voucher Is Created From Invoice/Purhcase# {gledg_to_update.get("INVOICE_ID")} So Update From Invoice/Purchase.',vno_to_update


    

    if not gledg_to_update and update:
        return False , "Voucher not found",0

    if update:
        fixed_filters = {
            'COMPANY': Company.objects.get(id=gledg_to_update.get('COMPANY')),
            'BRANCH': Branch.objects.get(id=gledg_to_update.get('BRANCH')),
            'POSTERMINAL': POSTerminal.objects.get(id=gledg_to_update.get('POSTERMINAL')),
        }
    else:
        fixed_filters = get_fixed_filters(request)


    current_datetime = get_server_datetime()

    date = date or current_datetime.date()

    vno = (
        gledg_to_update.get("VNO")
        if update
        else get_next_voucher((v_type if v_type!='ADJ' else 'JV') )
    )

    srno = get_srno(
        v_type=(v_type if v_type!='ADJ' else 'JV'),
        update=update,
        old_data=gledg_to_update,
    )

    common = {

        "V_TYPE": v_type if v_type != 'ADJ' else 'JV',
        "VNO": vno,
        "DATE": date,
        'INVOICE_ID':inv_id if inv_id else 0,
        
        "REMARKS": remarks[:60] if remarks else "",

        "PUR_INV": pur_inv,

        "DATEENT": (
            gledg_to_update.get("DATEENT")
            if update
            else current_datetime
        ),

        "DATEEDIT": timezone.now() if update else None,

        "USER": (
            gledg_to_update.get("USER")
            if update
            else request.user.username  if request else "system"
        ),

        "EDITBY": request.user.username  if request and update else "",

        "BRANCH": fixed_filters.get('BRANCH'),
        "COMPANY": fixed_filters.get('COMPANY'),
        "POSTERMINAL": fixed_filters.get('POSTERMINAL'),

        "SHIFT": "",

        "CHEQUE_DATE":None,

        "DRAWN_BRANCH": "",

        "PAYMENTMETHOD": "",

        "BANK_RECONCILE": None,

        "ISPOSTED": None,

        "SALES_MAN": None,

        # "STATION": "",

        "DEPT": "",
    }

    # Ensure default discount accounts exist
    from apps.myaccounts.models import Accounts
    from apps.myaccounts.constants import get_default_account
    sales_disc_acc_code = int(get_default_account('SALES_DISCOUNT_ACCOUNT', company_id=fixed_filters.get('COMPANY').id if fixed_filters.get('COMPANY') else None, branch_id=fixed_filters.get('BRANCH').id if fixed_filters.get('BRANCH') else None))
    pur_disc_acc_code = int(get_default_account('PURCHASE_DISCOUNT_ACCOUNT', company_id=fixed_filters.get('COMPANY').id if fixed_filters.get('COMPANY') else None, branch_id=fixed_filters.get('BRANCH').id if fixed_filters.get('BRANCH') else None))

    Accounts.objects.get_or_create(
        ACC_CODE=sales_disc_acc_code,
        defaults={
            'ACC_NAME': 'Sales Discount Given',
            'TYPE': 'Detail',
            'LEVEL': DETAIL_LEVEL,
            'CLASS_FIELD': 'Expanse',
        }
    )
    Accounts.objects.get_or_create(
        ACC_CODE=pur_disc_acc_code,
        defaults={
            'ACC_NAME': 'Purchase Discount Taken',
            'TYPE': 'Detail',
            'LEVEL': DETAIL_LEVEL,
            'CLASS_FIELD': 'Income',
        }
    )

    # Determine AMT_TYPE for user lines
    if v_type in ["CP", "BP"]:
        user_amt_type = "DR"
    elif v_type == "ADJ":
        user_amt_type = "DR" if transaction_type == "dvm_lessInSup" else "CR"
    else:
        user_amt_type = "CR"

    # Determine AMT_TYPE for system lines
    if v_type in ["CR", "BR"]:
        sys_amt_type = "DR"
    elif v_type == "ADJ":
        sys_amt_type = "CR" if transaction_type == "dvm_lessInSup" else "DR"
    else:
        sys_amt_type = "CR"

    entries = []
    unique_acc_amounts = defaultdict(Decimal)
    for line in lines:
        amount = Decimal(str(line.amount or 0))
        unique_acc_amounts[line.accCode] += amount
        line_amt_type = getattr(line, 'amtType', None) or user_amt_type
        entries.append(
            Gledg(
                ACC_CODE=line.accCode,
                REF_ACC_CODE=line.refAccCode,
                ACC_HEAD = line.head,
                AMOUNT=line.amount,
                AMT_TYPE=line_amt_type,
                SHOW_IN_SALE_RPT="Y",
                RECEIPTNO=line.receiptNo,
                CHQNO=line.chqNo,
                DESCRIPTION=line.notes,
                **common
            )
        )
        
    # system row
    if v_type != 'JV':
        for accCode, amount in unique_acc_amounts.items():
            # Get refAccCode from lines for the balancing account
            ref_acc = next((line.refAccCode for line in lines if line.accCode == accCode), None)
            if not ref_acc:
                comp_id = fixed_filters.get('COMPANY').id if fixed_filters.get('COMPANY') else None
                br_id = fixed_filters.get('BRANCH').id if fixed_filters.get('BRANCH') else None
                ref_acc = int(get_default_account('BANK_ACCOUNT', company_id=comp_id, branch_id=br_id)) if v_type in ['BR', 'BP'] else int(get_default_account('CASH_IN_HAND_ACCOUNT', company_id=comp_id, branch_id=br_id))
        
            entries.append(
                Gledg(
                    ACC_CODE=ref_acc,
                    REF_ACC_CODE=accCode,
                    AMOUNT=amount,
                    AMT_TYPE=sys_amt_type,
                    SHOW_IN_SALE_RPT="N",
                    **common
                )
            )
    

    with transaction.atomic():

        # --------------------------------
        # UPDATE MODE
        # --------------------------------

        if update:
            gledg_queryset.delete()

        Gledg.objects.bulk_create(entries)

    return True , f'Saved Successfully! Voucher No: {vno}', vno






def delete_gledg_entries(
    *,
    v_type,
    vno,
):


    try:
        with transaction.atomic():
            Gledg.objects.filter(
                V_TYPE=v_type if v_type != 'ADJ' else 'JV',
                VNO=vno
            ).delete()
        return {"success":True, "message": "Deleted Successfully"}
    except Exception as e:
        return {"success":False, "message": "Server Error"}
    
def get_gledg_entries(data:dict): 
    query = Gledg.objects.filter(V_TYPE=data['V_TYPE'],VNO=data['VNO']).values(
        'ACC_CODE',
        'ACC_HEAD',
        'REF_ACC_CODE',
        'AMOUNT',
        'AMT_TYPE',
        'RECEIPTNO',
        'CHQNO',
        'V_TYPE',
        'VNO',
        'DATE',
        'DESCRIPTION',
        'REMARKS',
    )
    
    return query
