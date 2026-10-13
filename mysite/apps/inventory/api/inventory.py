from django.http import JsonResponse
from django.db import transaction
from django.db.models import F
from apps.inventory.models import Inventory
from apps.inventory.forms.inventory import InventoryForm

from apps.myglobal.services.helpers import get_user_perms

def save_update_inventory(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    
    has_permission, message = get_user_perms(request, 'add_item')
    if not has_permission:
        return JsonResponse({'success': False, 'error': message}, status=403)

    company = request.user.userprofile.company
    branch = request.user.userprofile.branch
    
    old_inv_id = request.POST.get('inv_id')
    if old_inv_id:
        has_permission, message = get_user_perms(request, 'edit_item')
        if not has_permission:
            return JsonResponse({'success': False, 'error': message}, status=403)
        try:
            # print('old id exist')
            old_inv_obj = Inventory.objects.get(company=company, branch=branch, inv_id=old_inv_id)
            # print(old_inv_obj, '___________________________',old_inv_id)
            form = InventoryForm(request.POST, request.FILES, instance=old_inv_obj)
            message = 'Updated successfully!'
        except Inventory.DoesNotExist:
            has_permission, message = get_user_perms(request, 'add_item')
            if not has_permission:
                return JsonResponse({'success': False, 'error': message}, status=403)
            form = InventoryForm(request.POST, request.FILES)
            message = 'Created successfully!'
    else:
        has_permission, message = get_user_perms(request, 'add_item')
        if not has_permission:
            return JsonResponse({'success': False, 'error': message}, status=403)
        form = InventoryForm(request.POST, request.FILES)
        message = 'Created successfully!'
        
    if form.is_valid():
        try:
            with transaction.atomic():
                instance = form.save(commit=False)
                # print(instance.inv_id, 'instance inv_id___________________________',old_inv_id)
                instance.company = company
                instance.branch = branch
                
                is_update = instance.pk is not None
                if not is_update:
                    instance.user = request.user.username if request.user.is_authenticated else 'system'
                else:
                    instance.updated_by = request.user.username if request.user.is_authenticated else 'system'
                    
                has_new_image = 'prod_picture' in request.FILES
                delete_image = request.POST.get('delete_image') == 'true'

                if delete_image and not has_new_image:
                    instance.prod_picture.delete(save=False)
                    instance.prod_picture_thumb.delete(save=False)
                    instance.image_updated_at = None

                instance.save()
                
                if has_new_image:
                    from apps.inventory.services.image_service import process_product_image
                    try:
                        from django.utils import timezone
                        process_product_image(instance)
                        instance.image_updated_at = timezone.now()
                        instance.save(update_fields=['prod_picture','prod_picture_thumb','image_updated_at'])
                    except Exception as img_err:
                        print("Error processing image in API:", img_err)

                form.save_m2m()
                
                # Serialize form fields for UI response
                serialized_form = InventoryForm(instance=instance)
                data = {}
                for field in serialized_form:
                    if field.name == 'date' and field.value() is not None:
                        data[field.name] = field.value().strftime('%Y-%m-%d')
                    elif field.name == 'expiry_date' and field.value() is not None:
                        data[field.name] = field.value().strftime('%Y-%m-%d')
                    else:
                        data[field.name] = field.value()
                        
                # Add image URLs
                data['prod_picture_url'] = instance.prod_picture.url if instance.prod_picture else None
                data['prod_picture_thumb_url'] = instance.prod_picture_thumb.url if getattr(instance, 'prod_picture_thumb', None) and instance.prod_picture_thumb else None
                data['prod_picture'] = None
                data['prod_picture_thumb'] = None
                        
                # Serialize DB record for IndexedDB (annotate FK display names for UOM and category)
                db_record = Inventory.objects.filter(pk=instance.pk).annotate(
                    base_uom_name=F('base_uom__name'),
                    carton_uom_name=F('carton_uom__name'),
                    dzn_uom_name=F('dzn_uom__name'),
                    category_name=F('category__name'),
                ).values().first()
                
                return JsonResponse({
                    'success': True,
                    'message': message,
                    'data': data,
                    'db_record': db_record
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        # Return form validation errors
        errors = {field: error[0]['message'] for field, error in form.errors.get_json_data().items()}
        return JsonResponse({'success': False, 'errors': errors}, status=400)


def delete_inventory(request, inv_id):

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    has_permission, message = get_user_perms(request, 'delete_item')
    if not has_permission:
        return JsonResponse({'success': False, 'error': message}, status=403)
    
    company = request.user.userprofile.company
    branch = request.user.userprofile.branch
    
    try:
        old_inv_obj = Inventory.objects.get(company=company, branch=branch, inv_id=inv_id)
        if old_inv_obj:
            old_inv_obj.is_deleted = True
            old_inv_obj.save()
            return JsonResponse({'success': True, 'message': f'Deleted successfully! Inventory ID : {inv_id}'})
        # if old_inv_obj:
        #     old_inv_obj.delete()
        #     return JsonResponse({'success': True, 'message': f'Deleted successfully! Inventory ID : {inv_id}'})
        else:
            return JsonResponse({'success': False, 'message': f'Inventory not found Inventory ID : {inv_id}'}, status=404)
    except Inventory.DoesNotExist:
        return JsonResponse({'success': False, 'message': f'Inventory not found Inventory ID : {inv_id}'}, status=404)