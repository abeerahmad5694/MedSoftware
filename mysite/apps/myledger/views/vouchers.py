from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string


from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import render, redirect

def jv_voucher_page(request, v_type=None, vno=None):
    perm = 'edit_vouchers' if vno else 'create_vouchers'
    can_access, _ = get_user_perms(request, perm)
    if not can_access:
        return redirect('page_not_found')
        
    v_type = v_type.upper() if v_type else 'JV'
    vno = vno if vno else request.GET.get('vno')
    print('vno',vno)
    print('v_type',v_type)
    context = {
        'v_type': v_type,
        'vno': vno,
        'mode': 'page'
    }
    return render(request, 'myledger/vouchers/jv_voucher.html', context)

from apps.users.api.license import validate_license
@validate_license
def dynamic_voucher_page(request, v_type=None, vno=None):
    perm = 'edit_vouchers' if vno or request.GET.get('vno') else 'create_vouchers'
    can_access, _ = get_user_perms(request, perm)
    if not can_access:
        return redirect('page_not_found')
        
    v_type = v_type.upper() if v_type else request.GET.get('v_type', 'CR').upper()
    vno = vno if vno else request.GET.get('vno')
    print('vno',vno)
    print('v_type',v_type)
    context = {
        'v_type': v_type,
        'vno': vno,
        'mode': 'page'  
    }
    return render(request, 'myledger/vouchers/dynamic_voucher.html', context)