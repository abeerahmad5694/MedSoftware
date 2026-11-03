from apps.configuration.models import Branch
from apps.configuration.models import Company
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from apps.inventory.forms.inventory import InventoryForm
from apps.inventory.models import Inventory


from apps.myledger.services.helpers import get_user_perms
from apps.users.api.license import validate_license


from apps.inventory.services.image_service import process_product_image









# inventory/seed_laptop_masters.py
from django.db import transaction
from apps.inventory.models import ItemBrand, ItemCategory, Inventory
# Adjust import path to your app: from your_app.models import ...

# ============================================================
# MASTER LIST - Brand -> [Master Names]
# Master = Main Model + Screen Size ONLY
# Processor / RAM / SSD / Color goes in Serial Row (Variant)
# ============================================================

LAPTOP_MASTERS = {
    "HP": [
        "HP 14 (14\")",
        "HP 15 (15.6\")",
        "HP 17 (17.3\")",
        "HP Pavilion 14 (14\")",
        "HP Pavilion 15 (15.6\")",
        "HP Pavilion x360 14 (14\")",
        "HP OmniBook 5 15 (15.6\")",
        "HP OmniBook X 14 (14\")",
        "HP ProBook 440 G11 (14\")",
        "HP ProBook 450 G10 (15.6\")",
        "HP ProBook 450 G11 (15.6\")",
        "HP EliteBook 840 G10 (14\")",
        "HP EliteBook 840 G11 (14\")",
        "HP EliteBook 1040 G11 (14\")",
        "HP EliteBook x360 830 G11 (13.3\")",
        "HP Victus 15 (15.6\")",
        "HP Victus 16 (16\")",
        "HP OMEN 16 (16\")",
        "HP OMEN 17 (17.3\")",
        "HP ZBook Firefly 14 G11 (14\")",
        "HP ZBook Power 15 G11 (15.6\")",
    ],
    "Dell": [
        "Dell Inspiron 14 (14\")",
        "Dell Inspiron 15 (15.6\")",
        "Dell Inspiron 16 (16\")",
        "Dell Inspiron 14 2-in-1 (14\")",
        "Dell Vostro 14 (14\")",
        "Dell Vostro 15 (15.6\")",
        "Dell Latitude 3440 (14\")",
        "Dell Latitude 3540 (15.6\")",
        "Dell Latitude 5440 (14\")",
        "Dell Latitude 5540 (15.6\")",
        "Dell Latitude 7440 (14\")",
        "Dell Latitude 9450 2-in-1 (14\")",
        "Dell XPS 13 (13.4\")",
        "Dell XPS 14 (14.5\")",
        "Dell XPS 16 (16.3\")",
        "Dell Pro 14 (14\")",
        "Dell Pro 16 (16\")",
        "Dell G15 (15.6\")",
        "Dell G16 (16\")",
        "  Alienware m16 (16\")",
        "  Precision 3581 (15.6\")",
    ],
   "Lenovo": [
        "  IdeaPad 1 14 (14\")",
        "  IdeaPad 1 15 (15.6\")",
        "  IdeaPad Slim 3 14 (14\")",
        "  IdeaPad Slim 3 15 (15.6\")",
        "  IdeaPad Slim 5 14 (14\")",
        "  Yoga 7 2-in-1 14 (14\")",
        "  ThinkPad E14 Gen 5 (14\")",
        "  ThinkPad E15 Gen 4 (15.6\")",
        "  ThinkPad T14 Gen 4 (14\")",
        "  ThinkPad T14 Gen 5 (14\")",
        "  ThinkPad T16 Gen 3 (16\")",
        "  ThinkPad X1 Carbon Gen 11 (14\")",
        "  ThinkPad X1 Carbon Gen 12 (14\")",
        "  ThinkPad L14 Gen 4 (14\")",
        "  ThinkBook 14 Gen 7 (14\")",
        "  ThinkBook 15 Gen 5 (15.6\")",
        "  LOQ 15 (15.6\")",
        "  LOQ 16 (16\")",
        "  Legion 5 15 (15.6\")",
        "  Legion Pro 5 16 (16\")",
        "  Legion Slim 5 14 (14\")",
        "  ThinkPad P14s Gen 4 (14\")",
        "  ThinkPad P16 Gen 2 (16\")",
    ],
    "Apple": [
        "MacBook Air M1 13 (13.3\")",
        "MacBook Air M2 13 (13.6\")",
        "MacBook Air M2 15 (15.3\")",
        "MacBook Air M3 13 (13.6\")",
        "MacBook Air M3 15 (15.3\")",
        "MacBook Air M4 13 (13.6\")",
        "MacBook Air M4 15 (15.3\")",
        "MacBook Pro M1 13 (13.3\")",
        "MacBook Pro M2 13 (13.3\")",
        "MacBook Pro M3 14 (14.2\")",
        "MacBook Pro M3 Pro 14 (14.2\")",
        "MacBook Pro M4 16 (16.2\")",
    ],
    "Toshiba": [
        "Toshiba Dynabook Satellite Pro C40 (14\")",
        "Toshiba Dynabook Tecra A40 (14\")",
        "Toshiba Dynabook Portege X30 (13.3\")",
        "Toshiba Dynabook Portege X40 (14\")",
        "Toshiba Satellite L50 (15.6\")",
        "Toshiba Satellite Pro R50 (15.6\")",
    ],
    "Acer": [
        "   Aspire 3 14 (14\")",
        "   Aspire 5 15 (15.6\")",
        "   Swift 3 14 (14\")",
        "   Nitro 5 15 (15.6\")",
        "   Predator Helios 16 (16\")",
    ],
    "Asus": [
        "Asus VivoBook 14 (14\")",
        "Asus VivoBook 15 (15.6\")",
        "Asus ZenBook 14 (14\")",
        "Asus ROG Strix G15 (15.6\")",
        "Asus ROG Strix G16 (16\")",
        "Asus TUF Gaming F15 (15.6\")",
        "Asus TUF Gaming A15 (15.6\")",
    ],
    "MSI": [
        "MSI Modern 14 (14\")",
        "MSI Katana 15 (15.6\")",
        "MSI Cyborg 15 (15.6\")",
        "MSI Stealth 16 (16\")",
    ],
}

@transaction.atomic
def seed_laptop_masters(company, branch, user="admin"):
    """
    Creates 100+ Laptop Parent Masters.
    Run once per Company/Branch.
    Safe to run again - it will NOT duplicate.
    Usage:
        from inventory.seed_laptop_masters import seed_laptop_masters
        seed_laptop_masters(company_obj, branch_obj)
    """
    # 1. Category = Laptop (common for all)
    category = ItemCategory.objects.filter(
        company=company, branch=branch, name__iexact="Laptop"
    ).first()
    if not category:
        category = ItemCategory.objects.create(
            company=company, branch=branch, name="Laptop"
        )

    created = 0
    skipped = 0

    for brand_name, master_names in LAPTOP_MASTERS.items():
        # 2. Brand = HP /   /   ...
        brand_name = brand_name.strip()

        brand = ItemBrand.objects.filter(
            company=company, branch=branch, name__iexact=brand_name
        ).first()
        if not brand:
            brand = ItemBrand.objects.create(
                company=company, branch=branch, name=brand_name
            )

        for prod_name in master_names:
            # 3. Check if already exists - prevent duplicate
            exists = Inventory.objects.filter(
                company=company,
                branch=branch,
                prod_name=prod_name,
                brand=brand,
                is_variant=False,
                is_deleted=False,
            ).exists()

            if exists:
                skipped += 1
                continue

            # 4. Create PARENT Master
            # Parent has NO serial_no, NO stock, NO cost
            # It is only for grouping + searching
            Inventory.objects.create(
                company=company,
                branch=branch,
                prod_name=prod_name,
                alias_name=prod_name,  # for fast search
                brand=brand,
                category=category,
                # --- LAPTOP TRACKING ---
                tracking_type="SERIAL",  # SERIAL = Laptop/Mobile
                is_variant=False,        # False = Parent / Master
                parent_item=None,        # Parent has no parent
                variant_title="",        # Parent has no variant title
                # --- Specs empty on Parent ---
                # Processor / RAM / Storage / Color will go on CHILD Variant (serial row)
                processor="",
                ram="",
                storage="",
                color="",
                serial_no=None,
                serial_no2="",
                condition="NEW",
                status="IN_STOCK",
                # --- Stock / Price ---
                bal_qty=0,
                remaining_qty=0,
                cost=0,
                individual_cost=None,
                extra_cost=0,
                ws_price=None,
                market_price=None,
                active=True,
                is_deleted=False,
                user=user,
            )
            created += 1

    return {"created": created, "skipped": skipped, "total": created + skipped}

# ============================================================
# BONUS: Function to create a CHILD Variant (Serial Piece)
# Use this in your Purchase screen when user adds a serial row
# ============================================================

@transaction.atomic
def create_laptop_serial_piece(
    company, branch, parent_master, serial_no,
    processor, ram, storage, color,
    condition="NEW", individual_cost=0,
    warranty_end=None, user="admin"
):
    """
    Example:
        parent = Inventory.objects.get(prod_name='HP 15 (15.6")', is_variant=False)
        create_laptop_serial_piece(
            company, branch, parent,
            serial_no="5CG1234567",
            processor="Core i5 13th - 1335U",
            ram="16GB", storage="512GB SSD", color="Silver",
            condition="NEW", individual_cost=185000,
            warranty_end=date(2027, 11, 3)
        )
    """
    # 1. Prevent duplicate serial
    if Inventory.objects.filter(
        company=company, serial_no=serial_no, is_deleted=False
    ).exists():
        raise ValueError(f"Serial {serial_no} already exists!")

    # 2. Create Variant - Qty is always 1 for serial
    variant = Inventory.objects.create(
        company=company,
        branch=branch,
        prod_name=parent_master.prod_name,  # Same name as parent
        alias_name=f"{parent_master.prod_name} - {serial_no}",
        brand=parent_master.brand,
        category=parent_master.category,
        tracking_type="SERIAL",
        is_variant=True,  # True = Real piece
        parent_item=parent_master,
        variant_title=f"{processor} / {ram} / {storage} / {color}",
        processor=processor,
        ram=ram,
        storage=storage,
        color=color,
        serial_no=serial_no,
        condition=condition,
        status="IN_STOCK",
        individual_cost=individual_cost,
        extra_cost=0,
        bal_qty=1,  # 1 piece = 1 qty
        remaining_qty=1,
        warranty_end=warranty_end,
        active=True,
        user=user,
    )
    return variant


















@validate_license
@transaction.atomic
def inventory(request):
    
    # company = Company.objects.first()
    # branch = Branch.objects.first()
    # result = seed_laptop_masters(company, branch
    
    
    
    can_view, message = get_user_perms(request, 'view_inventory')
    if not can_view:
        return redirect('page_not_found')
    
    # Inventory.objects.all().delete()
    company = request.user.userprofile.company
    branch = request.user.userprofile.branch
    form = InventoryForm()
    if request.method=='POST':
        try:
            with transaction.atomic():
                old_inv_id = request.POST.get('inv_id')
                if old_inv_id:
                    try:
                        old_inv_obj = Inventory.objects.get(inv_id=old_inv_id)
                        form = InventoryForm(request.POST, request.FILES, instance=old_inv_obj)
                    except Inventory.DoesNotExist:
                        form = InventoryForm(request.POST, request.FILES)
                else:
                    form = InventoryForm(request.POST, request.FILES)
                if form.is_valid():
                    inv_instance = form.save(commit=False)
                    inv_instance.company = company
                    inv_instance.branch = branch





                    has_new_image = 'prod_picture' in request.FILES
                    delete_image = request.POST.get('delete_image') == 'true'

                    if delete_image and not has_new_image:
                        inv_instance.prod_picture.delete(save=False)
                        inv_instance.prod_picture_thumb.delete(save=False)
                        inv_instance.image_updated_at = None

                    inv_instance.save()
                    if has_new_image:
                        process_product_image(inv_instance)
                        inv_instance.image_updated_at = timezone.now()
                        inv_instance.save(update_fields=['prod_picture','prod_picture_thumb','image_updated_at'])




                    # inv_instance.save()
                    return redirect('inventory')
                else:
                    print(form.errors)
                    return redirect('inventory')
        except Exception as e:
            print(f"Error saving inventory item: {e}")
            return redirect('inventory')

    some_inventory_products = Inventory.objects.filter(company =company, branch = branch).values('inv_id','prod_name', 'prod_picture_thumb').order_by('-inv_id')[:15] 
    context = {
        'form': form,
        'company_id': company.id,
        'branch_id': branch.id,
        'some_inventory_products':some_inventory_products
    }
    return render(request, 'inventory/inventory.html', context)




def get_item_by_id(request, inv_id):
    inventory = Inventory.objects.filter(
        company=request.user.userprofile.company, 
        branch=request.user.userprofile.branch, 
        inv_id=inv_id
    ).first()
    
    if not inventory:
        return JsonResponse({'success':False, 'message':'Item not found. Please Refresh Your Offline Inventory!'})

    # FIXED: Build data manually, skip file fields
    data = {}
    
    # Get all concrete fields except files
    for field in Inventory._meta.concrete_fields:
        field_name = field.name
        if field_name in ['company', 'branch', 'prod_picture', 'prod_picture_thumb']:
            continue
            
        value = getattr(inventory, field_name)
        
        if value is None:
            data[field_name] = None
        elif hasattr(value, 'strftime'):  # date/datetime
            data[field_name] = value.strftime('%Y-%m-%d')
        elif hasattr(field, 'related_model') and field.related_model:  # FK
            data[field_name] = value.pk if value else None
        else:
            data[field_name] = value

    data['inv_id'] = inventory.inv_id
    
    # Add image urls separately as strings
    try:
        data['prod_picture_url'] = inventory.prod_picture.url if inventory.prod_picture else None
    except:
        data['prod_picture_url'] = None
        
    try:
        data['prod_picture_thumb_url'] = inventory.prod_picture_thumb.url if getattr(inventory, 'prod_picture_thumb', None) and inventory.prod_picture_thumb else None
    except:
        data['prod_picture_thumb_url'] = None

    # For backward compatibility, don't send file objects
    data['prod_picture'] = None
    data['prod_picture_thumb'] = None

    return JsonResponse({'success':True, 'data':data})




# def get_item_by_id(request , inv_id):
#     inventory = Inventory.objects.filter(company = request.user.userprofile.company, branch = request.user.userprofile.branch, inv_id=inv_id).first()
#     if not inventory:
#         return JsonResponse({'success':False, 'message':'Item not found. Pleae Refresh Your Offline Inventory!'})

#     form = InventoryForm(instance=inventory)
#     data = {}
#     for field in form:
#         # print(field.name)
#         data[field.name] = field.value()
#         if field.name == 'date' and field.value() is not None:
#             data[field.name] = field.value().strftime('%Y-%m-%d')
#         elif field.name == 'expiry_date' and field.value() is not None:
#             data[field.name] = field.value().strftime('%Y-%m-%d')
#         else:
#             data[field.name] = field.value()

#     data['inv_id'] = inventory.inv_id
#     if inventory.prod_picture:
#         data['prod_picture_url'] = inventory.prod_picture.url
#     if inventory.prod_picture_thumb:
#         data['prod_picture_thumb_url'] = inventory.prod_picture_thumb.url
#     return JsonResponse({'success':True, 'data':data})