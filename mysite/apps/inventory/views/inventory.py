from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.db import transaction
from apps.inventory.forms.inventory import InventoryForm
from apps.inventory.models import Inventory


from apps.myledger.services.helpers import get_user_perms
from apps.users.api.license import validate_license


from apps.inventory.services.image_service import process_product_image

@validate_license
@transaction.atomic
def inventory(request):
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