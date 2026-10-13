from django.http import JsonResponse
# from django.contrib.auth.decorators import login_required
from django.apps import apps
from django.db.models import Q
from django.core.paginator import Paginator

# ══════════════════════════════════════════════════════════════
# SEARCH REGISTRY — Full control per model
# Add new models here to make them searchable via GlobalSearchModal.
# ══════════════════════════════════════════════════════════════
SEARCH_REGISTRY = {
    'inventory.Inventory': {
        'primary_key': 'inv_id',
        'search_fields': ['prod_name', 'alias_name', 'barcode', 'manualbc'],
        'display_fields': ['inv_id', 'prod_name', 'barcode', 'base_price'],
        'display_headers': ['ID', 'Product Name', 'Barcode', 'Price'],
        'return_fields': ['inv_id', 'prod_name', 'base_price', 'barcode', 'alias_name', 'ws_price', 'carton_price', 'dzn_price', 'category__name'],
        'default_order': 'prod_name',
        'page_size': 50,
        # 'filters': {'TYPE': 'Detail'},   # auto-applied WHERE clause
        'exclude': {},                  # auto-applied exclude
    },
    'myaccounts.Accounts': {
        'primary_key': 'ACC_CODE',
        'search_fields': ['ACC_CODE','ACC_NAME'],   
        'display_fields': ['ACC_CODE','ACC_NAME'],
        'display_headers': ['ACC_CODE','ACC_NAME'],
        'return_fields': ['ACC_CODE','ACC_NAME'],
        'default_order': 'ACC_CODE',
        'page_size': 50,
        'user_required': False,
        'company_required': False,
        'filters': {'TYPE__exact': 'Detail'},   # auto-applied WHERE clause
        'exclude': {},                  # auto-applied exclude
    },
}

# if q = int and len(q) < 13 then first check the exact match to inv_id or acc_code for account model , if len(q) => 13 then check search amon barcode and barcode 2 field in inventory for exact value 
# 
# if q = string  then check  first exact manual_bc then barcode2 then exact alias name  then fuzzy search on prod_name then exact barcoe and exact inv_id like google search engine 
# 
#   
# SEARCH_PRIORITY_CONFIG=[]



def global_search(request, app_label, model_name):
    """
    Generic paginated search API.

    GET /mysearch/search/<app_label>/<model_name>/?q=term&page=1&page_size=50
    """

    registry_key = f'{app_label}.{model_name}'
    config = SEARCH_REGISTRY.get(registry_key)

    if not config:
        return JsonResponse({
            'success': False,
            'error': 'Model not registered for search'
        }, status=403)

    # Configurable flags
    user_required = config.get('user_required', False)
    company_required = config.get('company_required', False)

    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return JsonResponse({
            'success': False,
            'error': 'Model not found'
        }, status=404)

    user_profile = None

    # User validation
    if user_required:

        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=403)

        user_profile = getattr(request.user, 'userprofile', None)

        if not user_profile:
            return JsonResponse({
                'success': False,
                'error': 'User profile missing'
            }, status=403)

    # Request params
    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = int(
        request.GET.get(
            'page_size',
            config.get('page_size', 10)
        )
    )
    page_size = min(max(1, page_size), 100)

    # Base queryset
    qs = model.objects.all()

    # Company scoping only if enabled
    if company_required:

        if not user_profile:
            user_profile = getattr(request.user, 'userprofile', None)

        if not user_profile or not hasattr(user_profile, 'company'):
            return JsonResponse({
                'success': False,
                'error': 'Company information missing'
            }, status=403)

        qs = qs.filter(company=user_profile.company)

    # Registry filters
    if config.get('filters'):
        qs = qs.filter(**config['filters'])

    # Registry excludes
    if config.get('exclude'):
        qs = qs.exclude(**config['exclude'])

    # Search logic
    if query:

        q_objects = Q()

        primary_key = config.get('primary_key', 'pk')

        # Exact numeric PK match
        if query.isdigit():
            q_objects |= Q(**{primary_key: int(query)})

        # icontains search
        for field in config.get('search_fields', []):
            q_objects |= Q(**{f'{field}__icontains': query})

        qs = qs.filter(q_objects)

    # Ordering
    qs = qs.order_by(config.get('default_order', 'pk'))

    # Pagination
    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    # Merge fields
    all_fields = list(dict.fromkeys(
        config.get('display_fields', []) +
        config.get('return_fields', [])
    ))

    results = []

    for item in page_obj:

        row = {}

        for field in all_fields:

            if '__' in field:

                obj = item

                for part in field.split('__'):
                    obj = getattr(obj, part, None)

                    if obj is None:
                        break

                row[field] = str(obj) if obj is not None else ''

            else:

                val = getattr(item, field, None)

                if val is None:
                    row[field] = ''

                elif hasattr(val, 'as_integer_ratio'):
                    row[field] = float(val)

                else:
                    row[field] = val

        results.append(row)

    return JsonResponse({
        'success': True,
        'results': results,
        'page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_count': paginator.count,
        'display_headers': config.get('display_headers', all_fields),
        'display_fields': config.get('display_fields', all_fields),
    })
    
