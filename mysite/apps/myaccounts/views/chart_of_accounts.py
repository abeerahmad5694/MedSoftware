from django.shortcuts import render, redirect
from django.contrib import messages
from apps.myaccounts.services.accounts_utills import generate_next_account_code
from apps.myaccounts.models import Accounts
from apps.myaccounts.forms import AccountsForm




from apps.myledger.services.helpers import get_user_perms

def chart_of_accounts(request):
    can_view, _ = get_user_perms(request, 'edit_accounts')
    if not can_view:
        return redirect('page_not_found')
    return render(request, 'myaccounts/chart_of_accounts.html')