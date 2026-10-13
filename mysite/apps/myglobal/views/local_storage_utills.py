

    
    
    

from apps.inventory.models import (
    ItemBrand, 
    ItemCompany,
    ItemCategory,
    ItemSubCategory,
    Unit,
    Inventory,

)   

from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.apps import apps
from apps.myglobal.services.helpers import DateTimeHelper
from django.utils.dateparse import parse_datetime
from django.db.models import F

datetime_helper = DateTimeHelper()





from django.db.models import Q, F
from django.forms.models import model_to_dict

EXCLUDE_FILE_FIELDS = ['prod_picture', 'prod_picture_thumb', 'prod_picture_url', 'prod_picture_thumb_url']  # add any other file field names

def fetch_full_model(request, app_label, model_name):
    include_in_filter = {
        'company': request.user.userprofile.company,
        'active': True,
        'is_deleted': False,
    }
    try:
        model = apps.get_model(app_label, model_name)
        qs = model.objects.filter(**include_in_filter)
        
        if model_name == 'Inventory':
            qs = qs.select_related('base_uom', 'carton_uom', 'dzn_uom', 'category').order_by('inv_id')
        
        data = []
        for item in qs:
            # 1. Exclude file fields - THIS FIXES ImageFieldFile error
            d = model_to_dict(item, exclude=EXCLUDE_FILE_FIELDS)
            
            pk_name = item._meta.pk.name
            d[pk_name] = item.pk

            if model_name == 'Inventory':
                # 2. Add display names
                d['base_uom_name'] = str(item.base_uom) if item.base_uom else None
                d['carton_uom_name'] = str(item.carton_uom) if item.carton_uom else None
                d['dzn_uom_name'] = str(item.dzn_uom) if item.dzn_uom else None
                d['category_name'] = str(item.category) if item.category else None
                
                # 3. Add image URLs as STRING, not file object
                try:
                    d['prod_picture_url'] = item.prod_picture.url if item.prod_picture else None
                except:
                    d['prod_picture_url'] = None
                try:
                    d['prod_picture_thumb_url'] = item.prod_picture_thumb.url if item.prod_picture_thumb else None
                except:
                    d['prod_picture_thumb_url'] = None
                # Also keep raw path for offline if needed
                d['prod_picture'] = item.prod_picture.name if item.prod_picture else None
                d['prod_picture_thumb'] = item.prod_picture_thumb.name if item.prod_picture_thumb else None

            data.append(d)
            
        return JsonResponse({'success': True, 'results': data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})

def sync_indexdb(request, app_label, model_name):
    try:
        Model = apps.get_model(app_label, model_name)
        filters = {
            'company': request.user.userprofile.company,
            'active': True,
            'is_deleted': False,
        }
        since = request.GET.get('since', None)

        if since:
            since_dt = parse_datetime(since)
            items = Model.objects.filter(**filters).filter(
                Q(updated_at__gt=since_dt) | Q(dateent__gt=since_dt)
            ).order_by("-updated_at")
        else:
            items = Model.objects.filter(**filters).order_by("-dateent")[:1000]

        # For Inventory, don't use values() directly - it still includes file fields as File object on some Django versions
        if model_name == 'Inventory':
            # Use values_list with specific fields you need for POS offline
            # Exclude prod_picture file object, include only name
            fields = [f.name for f in Model._meta.concrete_fields if f.name not in ['prod_picture', 'prod_picture_thumb']]
            # add url fields manually later
            data = list(items.values(*fields, 'base_uom__name', 'carton_uom__name', 'dzn_uom__name', 'category__name'))
            
            # Add image urls by fetching again with small loop - for 1000 items it's fine
            # If you want faster, just build thumb url: f"/media/items/{company.id}/{branch.id}/{inv_id}_thumb.webp"
            for row in data:
                inv_id = row['inv_id']
                company_id = request.user.userprofile.company.id
                branch_id = request.user.userprofile.branch.id
                # deterministic urls - no DB hit
                row['prod_picture_url'] = f"/media/items/{company_id}/{branch_id}/{inv_id}.webp"
                row['prod_picture_thumb_url'] = f"/media/items/{company_id}/{branch_id}/{inv_id}_thumb.webp"
                # keep legacy fields as string path
                row['prod_picture'] = f"items/{company_id}/{branch_id}/{inv_id}.webp"
                row['prod_picture_thumb'] = f"items/{company_id}/{branch_id}/{inv_id}_thumb.webp"
        else:
            data = list(items.values())

        last_updated_at = datetime_helper.get_server_time().isoformat()
        return JsonResponse({'success': True, 'results': data, 'last_updated_at': last_updated_at})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
    
    
    
    

# from apps.inventory.models import (
#     ItemBrand, 
#     ItemCompany,
#     ItemCategory,
#     ItemSubCategory,
#     Unit,
#     Inventory,

# )   

# from django.forms.models import model_to_dict
# from django.http import JsonResponse
# from django.apps import apps
# from apps.myglobal.services.helpers import DateTimeHelper
# from django.utils.dateparse import parse_datetime
# from django.db.models import F

# datetime_helper = DateTimeHelper()



# def fetch_full_model(request, app_label, model_name):

#     include_in_filter = {
#         'company' : request.user.userprofile.company,
#         'active' : True,
#         'is_deleted':False,
#     }
    
#     try:
#         model = apps.get_model(app_label, model_name)
#         items = model.objects.filter(**include_in_filter).select_related(
#             'base_uom', 'carton_uom', 'dzn_uom', 'category'
#         ).order_by('inv_id') if model_name == 'Inventory' else model.objects.filter(**include_in_filter)
#         data = []
#         for item in items:
#             d = model_to_dict(item)
#             # Ensure PK is always included (AutoField is non-editable, model_to_dict skips it)
#             pk_name = item._meta.pk.name
#             d[pk_name] = item.pk
#             # Add FK display names for UOM and category fields
#             if model_name == 'Inventory':
#                 d['base_uom_name'] = str(item.base_uom) if item.base_uom else None
#                 d['carton_uom_name'] = str(item.carton_uom) if item.carton_uom else None
#                 d['dzn_uom_name'] = str(item.dzn_uom) if item.dzn_uom else None
#                 d['category_name'] = str(item.category) if item.category else None
#             data.append(d)
#         return JsonResponse({'success': True, 'results': data})
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)})    




# def sync_indexdb(request, app_label, model_name):
#     try:
#         # from apps.applabel.models import model_name
#         Model = apps.get_model(app_label, model_name)
#         filters = {
#             'company' : request.user.userprofile.company,
#             'active' : True,
#             'is_deleted':False,
#         }
#         since = request.GET.get('since', None)

#         print('since', since, ',,,,,,, request', request,'ModelName',model_name,'applable',app_label)
#         if since:
#             since_dt = parse_datetime(since)
#             # Use Q objects to utilize indexes on updated_at / dateent instead of dynamic Coalesce annotation
#             items = (
#                 Model.objects
#                 .filter(**filters)
#                 .filter(
#                     Q(updated_at__gt=since_dt) | Q(dateent__gt=since_dt)
#                 )
#                 .order_by("-updated_at")
#             )
#         else:
#             # If no sync date is provided, limit the initial sync size or fetch only the most recent records
#             items = (   
#                 Model.objects
#                 .filter(**filters)
#                 .order_by("-dateent")[:1000] # Cap the initial sync if token is missing to prevent server crashes
#             )


#         # print('items==============================',items)

#         # Add FK display names for Inventory UOM and category fields
#         if model_name == 'Inventory' and items.exists():
#             items = items.annotate(
#                 base_uom_name=F('base_uom__name'),
#                 carton_uom_name=F('carton_uom__name'),
#                 dzn_uom_name=F('dzn_uom__name'),
#                 category_name=F('category__name'),
#             )

#         data = list(items.values())

#         last_updated_at = datetime_helper.get_server_time().isoformat()

#         return JsonResponse({'success': True, 'results': data, 'last_updated_at': last_updated_at})
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)})    