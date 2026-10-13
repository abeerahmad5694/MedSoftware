from django.shortcuts import render
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.http import require_GET, require_POST
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import datetime
import pytz #type:ignore
import os
import base64
from django.db.models import Sum 
from django.forms.models import model_to_dict
from django.shortcuts import redirect
from Crypto.PublicKey import RSA #type:ignore
from Crypto.Signature import pkcs1_15 #type:ignore
from Crypto.Hash import SHA256 #type:ignore
from apps.inventory.models import Inventory
from apps.sale.models import Invoice,BarcodConfig , Features
from apps.myglobal.services.helpers import get_next_voucher
from apps.sale.helpers import json_to_invoice
karachi_tz = pytz.timezone('Asia/Karachi')




def sale_page(request):
    employee = Invoice.objects.filter(id=55).first()
    if employee:
            
        history = employee.history.all()
        if history:
            for record in history:
                print(
                    'Invoice History From django simple history library',
                    record.datent,
                    record.inv_id,
                    record.history_type
                )

    else:
        print('No history found ')
    now = datetime.datetime.now().strftime("%d/%m/%Y")
    try: 
        features = Features.objects.get(user=request.user)
    except:
        features, created = Features.objects.get_or_create(
            user="All Features",
            defaults={
                "pos_discount_per_item": True,
                "pos_load_prv_bill": True,
                "pos_disc_flat_limit": 0.0,
            }
        )
    
    user_profile = getattr(request.user, 'userprofile', None)
    company = getattr(user_profile, 'company', None)
    branch = getattr(user_profile, 'branch', None)
    from apps.configuration.selectors import get_company_config
    config_data, _ = get_company_config(company.id if company else None, branch.id if branch else None)

    print(config_data)
    return render(request, 'quotation/index.html', {
        "user": request.user,
        "date": now,
        "last_bill_amount":  0,
        # "last_bill_amount": round(last) or 0,
        "features":features,
        "config": config_data,
    })



def get_features(request):
    username = (
        request.user.username
        if request.user.is_authenticated
        else "All Features"
    )

    # 1️⃣ Try user-specific features
    features = Features.objects.filter(user=username).first()

    # 2️⃣ Fallback to global features
    if not features:
        features, created = Features.objects.get_or_create(
            user="All Features",
            defaults={
                "pos_discount_per_item": True,
                "pos_load_prv_bill": True,
                "pos_disc_flat_limit": 0.0,
            }
        )
    # barcode_config = BarcodConfig.objects.get_or_create(user = 'main_bc')
    barcode_config, created = BarcodConfig.objects.get_or_create(
    user="main_bc",
    defaults={
        "price_base": "N",        # Normal
        "total_bc_digits": 13,
        "left_delete": 2,
        "right_delete": 1,
        "item_bc": 5,
        "kg": 2,
        "grm": 3,
    }
    )
    data = model_to_dict(features)
    barcode_config = model_to_dict(barcode_config)
    return JsonResponse({"features":data,"barcode_config":barcode_config})



