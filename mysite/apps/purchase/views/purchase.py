from django.shortcuts import render
from datetime import datetime


def purchase(request):

    now = datetime.now().strftime("%d/%m/%Y")
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

    return render(request, 'sale/index.html', {
        "user": request.user,
        "date": now,
        "features":features
    })