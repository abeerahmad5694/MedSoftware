from apps.myaccounts.models import Accounts
from django.db.models.functions import Cast
from django.db.models import CharField
from django.db import transaction
from django.db.models import Max

from apps.myaccounts.constants import *


def get_class_field_and_account_type_by_starting_code(acc_code,level):
    
    class_field = ""
    acc_type = ""

    if level == DETAIL_LEVEL:
        acc_type = DETAIL
    else:
        acc_type = GROUP

    if str(acc_code).startswith('1'):
        class_field = "Assets"
    elif str(acc_code).startswith('2'):
        class_field = "Liability"
    elif str(acc_code).startswith('3'):
        class_field = "Expanse"
    elif str(acc_code).startswith('4'):
        class_field = "Income"
    
    else:
        class_field = ""
    
    return {
        "class_field": class_field,
        "account_type": acc_type
    }


@transaction.atomic
def generate_next_account_code(parent_acc_code, level):

    if not all([parent_acc_code, level]):
        print('In complete data for next account code!')
        return 0

    level = int(level)

  
    class_field,account_type = get_class_field_and_account_type_by_starting_code(parent_acc_code,level).values()

    parent_prefix = str(parent_acc_code)[: level - 1]

    queryset = Accounts.objects.filter(
        LEVEL=level,
        TYPE=account_type,
        ACC_CODE__startswith=parent_prefix
    ).only('ACC_CODE')

    last_acc_code = queryset.aggregate(
        max_code=Max("ACC_CODE")
    )["max_code"]

    # DETAIL ACCOUNT
    if level == DETAIL_LEVEL and account_type.lower() == DETAIL.lower():

        if last_acc_code:
            return last_acc_code + 1

        return int(f"{parent_prefix}000001")

    # GROUP ACCOUNT
    if account_type.lower() == GROUP.lower():

        if last_acc_code:
            suffix = str(last_acc_code)[level - 1:]
            print("suffix", suffix)
            return int(f"{parent_prefix}{int(suffix) + 1}")

        return int(f"{parent_prefix}1")

    return 0



# def generate_next_account_code(parent_acc_code,class_field,level,account_type):
#     acc_code = 0
#     lastnum = 0
#     detail_level = 5
    
#     if not parent_acc_code and not class_field and not level:
#         return acc_code
    
#     parent_acc_code = str((parent_acc_code)[:(level-1)])
#     last_acc_code_obj = Accounts.objects.annotate(str_acc_code = Cast('ACC_CODE',CharField())).filter(
#         str_acc_code__startswith = parent_acc_code, 
#         LEVEL = level, CLASS_FIELD = class_field ,  TYPE = account_type
#         ).only("ACC_CODE").order_by('-ACC_CODE').first()
    
#     last_acc_code = last_acc_code_obj.ACC_CODE if last_acc_code_obj else None
    
#     if(last_acc_code):     
#         if int(level) == detail_level and account_type=='detail':
#             acc_code = last_acc_code + 1
#         elif int(level) != detail_level and account_type=='group':
#             lastnum = str(last_acc_code)[(level-1):] or 0             
#             acc_code = f"{parent_acc_code}{int(lastnum)+1}"
        
#     else:
#         if int(level)== detail_level and account_type=='detail':
#             acc_code = int(f'{parent_acc_code}000001')
#         elif int(level) != detail_level and account_type=='group':
#             acc_code = int(f'{parent_acc_code}1')
         
#     print('next_acc_code',acc_code)
        
#     return acc_code 

