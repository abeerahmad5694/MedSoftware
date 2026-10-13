from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import connections
from apps.myledger.models import Gledg
from datetime import datetime


from django.views.decorators.csrf import ensure_csrf_cookie


from apps.myledger.services.helpers import get_user_perms

from apps.users.api.license import validate_license
@validate_license
@ensure_csrf_cookie
def general_ledger(request):
    can_view, _ = get_user_perms(request, 'view_ledger')
    if not can_view:
        return redirect('page_not_found')
    columns = [
        {"key": "v_type", "label": "VTYPE", "width": "46px"},
        {"key": "date", "label": "DATE", "width": "82px"},
        {"key": "vno", "label": "VCH #", "width": "64px"},
        {"key": "desc", "label": "DESCRIPTION", "width": "auto"},
        # {"key": "amount", "label": "AMOUNT", "width": "150px"},
        {"key": "debit", "label": "DEBIT (+)", "width": "150px"},
        {"key": "credit", "label": "CREDIT (-)", "width": "150px"},
        {"key": "balance", "label": "BALANCE", "width": "150px"},
    ]
    return render(request, "myledger/general_ledger.html", {"columns": columns})    