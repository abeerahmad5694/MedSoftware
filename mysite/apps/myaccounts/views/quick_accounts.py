from django.shortcuts import render, redirect
from django.contrib import messages
from apps.myaccounts.services.accounts_utills import generate_next_account_code
from apps.myaccounts.models import Accounts
from apps.myaccounts.forms import AccountsForm




from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def quick_accounts(request):

    
    from django.shortcuts import render, redirect
    from apps.myglobal.services.helpers import get_user_perms
    has_permission, message = get_user_perms(request, 'create_accounts')
    if not has_permission:
        return redirect( 'page_not_found')
    return render(request, 'myaccounts/quick_accounts.html')