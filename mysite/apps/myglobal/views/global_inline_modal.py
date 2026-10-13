from django.shortcuts import render
from django.apps import apps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

ALLOWED_MODELS = {
    'inventory': ['ItemBrand', 'ItemCompany', 'ItemCategory', 'ItemSubCategory', 'Unit','Location'],
    'configuration': ['Branch', 'POSTerminal'],
}

@login_required
def generic_lookup_create(request, app_label, model_name):
    """
    Generic view to list and create items for lookup tables (Categories, Brands, etc.)
    """
    if app_label not in ALLOWED_MODELS or model_name not in ALLOWED_MODELS[app_label]:
        return JsonResponse({'error': 'Unauthorized model or app'}, status=403)
    
    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return JsonResponse({'error': 'Model not found'}, status=404)
        
    user_profile = getattr(request.user, 'userprofile', None)
    if not user_profile:
        return JsonResponse({'error': 'User profile missing'}, status=403)

    if request.method == 'GET':
        query = request.GET.get('q', '')
        # Filter by company to ensure data isolation
        items = model.objects.filter(company=user_profile.company)
        if query:
            items = items.filter(name__icontains=query)
        
        # Order by name for consistent UI
        items = items.order_by('name')[:50] # Limit to 50 for performance
        
        data = [{'id': item.id,
         'name': item.name
         } for item in items]
        return JsonResponse({'results': data})

    elif request.method == 'POST':
        id = request.POST.get('id', '').strip()
        if id:
            obj = model.objects.get(id=id)
            obj.name = request.POST.get('name', '').strip()
            obj.save()
            return JsonResponse({
                'id': obj.id, 
                'name': obj.name, 
                'message': f'"{obj.name}" updated successfully'
            })
        
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)
        
        # Check if already exists in this company
        if model.objects.filter(company=user_profile.company, name__iexact=name).exists():
            return JsonResponse({'error': f'"{name}" already exists'}, status=400)
            
        try:
            # Create object with common fields
            obj = model.objects.create(
                name=name,
                company=user_profile.company,
                branch=user_profile.branch
            )
            return JsonResponse({
                'id': obj.id, 
                'name': obj.name, 
                'message': f'"{name}" created successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)