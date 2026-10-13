from django.shortcuts import render
# Create your views here.
from decimal import Decimal
from apps.inventory.models import Inventory
from apps.configuration.models import Company, Branch
import random
from apps.configuration.models import CompanyConfiguration
def create_dummy_inventory():
    company = Company.objects.first()
    branch = Branch.objects.first()

    products = []

    for i in range(1, 10001):

        # Purchase Cost
        purchase_price = Decimal(random.randint(20, 5000))

        # Selling Prices
        base_price = purchase_price + Decimal(random.randint(5, 100))
        ws_price = base_price + Decimal(random.randint(5, 50))
        market_price = ws_price + Decimal(random.randint(5, 100))

        # Quantities
        carton_qty = random.choice([6, 8, 10, 12, 24, 48])
        dzn_qty = 12

        # Discounts
        base_disc = Decimal(random.randint(0, 15))
        ws_disc = Decimal(random.randint(0, 10))
        carton_disc = Decimal(random.randint(0, 12))
        dzn_disc = Decimal(random.randint(0, 8))

        # Stock
        stock = random.randint(0, 500)

        products.append(
            Inventory(
                company=company,
                branch=branch,

                prod_name=f"Product {i}",
                alias_name=f"P{i}",

                barcode=f"100000{i}",
                manualbc=f"200000{i}",
                barcode2=f"300000{i}",

                last_pur_price=purchase_price,
                purchase_price=purchase_price,
                cost=purchase_price,

                base_price=base_price,
                ws_price=ws_price,
                market_price=market_price,

                carton_price=base_price * carton_qty,
                dzn_price=base_price * dzn_qty,

                carton_qty=carton_qty,
                dzn_qty=dzn_qty,

                ws_disc_per=ws_disc,
                base_disc_per=base_disc,
                carton_disc_per=carton_disc,
                dzn_disc_per=dzn_disc,

                bal_qty=stock,
                remaining_qty=stock,
                purchase_qty=stock,
                sold_qty=random.randint(0, stock),

                reorder=random.randint(5, 50),

                sold_price=Decimal(0),
                active=True,
            )
        )

    Inventory.objects.bulk_create(products, batch_size=1000)

    print("10000 products created successfully.")


from apps.configuration.selectors import get_company_config




from apps.users.api.license import validate_license
from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect

@validate_license
def purchase(request):
    can_view, _ = get_user_perms(request, 'view_own_purchases')
    can_create, _ = get_user_perms(request, 'create_purchase_invoice')
    if not (can_view or can_create):
        return redirect('page_not_found')
    # user_profile = getattr(request.user, 'userprofile', None)
    # company = getattr(user_profile, 'company', None)
    # branch = getattr(user_profile, 'branch', None)
    
    # config_data, _ = get_company_config(company.id if company else None, branch.id if branch else None)
    # purchase_config = config_data.get('purchase', {})
    
    return render(request, 'purchase.html')
    # return render(request, 'purchase.html', {"purchase_config": purchase_config})