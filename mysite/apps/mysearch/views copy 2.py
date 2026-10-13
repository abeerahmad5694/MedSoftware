from django.http import JsonResponse
from django.apps import apps
from django.db.models import Q, Value, Case, When, IntegerField
from django.core.paginator import Paginator

# ══════════════════════════════════════════════════════════════
# PRIORITY CONFIG - Change order/type here only
# lookup: exact | iexact | icontains | fulltext
# stop_if_found: True = Google type - if found, don't run next rules
# ══════════════════════════════════════════════════════════════
SEARCH_REGISTRY = {
    'inventory.Inventory': {
        'primary_key': 'inv_id',
        'display_fields': ['inv_id', 'prod_name', 'barcode', 'base_price'],
        'display_headers': ['ID', 'Product Name', 'Barcode', 'Price'],
        'return_fields': ['inv_id', 'prod_name', 'base_price', 'barcode', 'alias_name', 'ws_price', 'carton_price', 'dzn_price', 'category__name'],
        'default_order': 'prod_name',
        'page_size': 50,
        'filters': {},
        'exclude': {},
        'company_required': True,

        'pipelines': [
            # PIPELINE 1: NUMERIC
            {
                'condition': lambda q: q.isdigit(),
                'rules': [
                    # len < 13 -> inv_id exact O(log n)
                    {'if': lambda q: len(q) < 13, 'field': 'inv_id', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                    # len >=13 -> barcode exact O(log n)
                    {'if': lambda q: len(q) >= 5, 'field': 'barcode', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 13, 'field': 'barcode2', 'lookup': 'exact', 'rank': 95, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 5, 'field': 'manualbc', 'lookup': 'exact', 'rank': 90, 'stop_if_found': True},
                    # fallback if numeric but no exact
                    {'field': 'alias_name', 'lookup': 'iexact', 'rank': 50},
                    {'field': 'prod_name', 'lookup': 'icontains', 'rank': 10},
                ]
            },
            # PIPELINE 2: STRING - Google Order
            {
                'condition': lambda q: not q.isdigit(),
                'rules': [
                    {'field': 'manualbc', 'lookup': 'iexact', 'rank': 100, 'stop_if_found': True},
                    {'field': 'barcode2', 'lookup': 'iexact', 'rank': 90, 'stop_if_found': True},
                    {'field': 'alias_name', 'lookup': 'iexact', 'rank': 80, 'stop_if_found': True},
                    # Fuzzy - uses FULLTEXT if available else icontains
                    {'field': 'prod_name', 'lookup': 'fulltext', 'rank': 60},
                    {'field': 'barcode', 'lookup': 'iexact', 'rank': 30},
                    {'field': 'inv_id', 'lookup': 'icontains', 'rank': 10},
                ]
            }
        ]
    },
    'myaccounts.Accounts': {
        'primary_key': 'ACC_CODE',
        'display_fields': ['ACC_CODE','ACC_NAME'],
        'display_headers': ['ACC_CODE','ACC_NAME'],
        'return_fields': ['ACC_CODE','ACC_NAME'],
        'default_order': 'ACC_CODE',
        'page_size': 50,
        'filters': {'TYPE__exact': 'Detail'},
        'exclude': {},
        'company_required': True,
        'pipelines': [
            {
                'condition': lambda q: True,
                'rules': [
                    {'if': lambda q: q.isdigit() and len(q) < 13, 'field': 'ACC_CODE', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 13, 'field': 'ACC_CODE', 'lookup': 'exact', 'rank': 90}, # if someone scans long code
                    {'field': 'ACC_NAME', 'lookup': 'fulltext', 'rank': 50},
                    {'field': 'ACC_NAME', 'lookup': 'icontains', 'rank': 20},
                ]
            }
        ]
    },
}

def _apply_lookup(qs, field, lookup, query):
    """O(log n) for exact, O(log n) for fulltext"""
    if lookup == 'exact':
        # handle int PK
        try:
            if field in ['inv_id', 'ACC_CODE']:
                return qs.filter(**{field: int(query)})
        except ValueError:
            pass
        return qs.filter(**{field: query})
    elif lookup == 'iexact':
        return qs.filter(**{f"{field}__iexact": query})
    elif lookup == 'fulltext':
        # For MySQL - will use FULLTEXT index if exists, else fallback
        # For prod_name we try fulltext search simulation via icontains but ranked
        return qs.filter(**{f"{field}__icontains": query})
    else: # icontains
        return qs.filter(**{f"{field}__icontains": query})

def global_search(request, app_label, model_name):
    registry_key = f'{app_label}.{model_name}'
    config = SEARCH_REGISTRY.get(registry_key)
    if not config:
        return JsonResponse({'success': False, 'error': 'Model not registered'}, status=403)

    try:
        model = apps.get_model(app_label, model_name)
    except LookupError:
        return JsonResponse({'success': False, 'error': 'Model not found'}, status=404)

    # Auth / Company check
    user_profile = getattr(request.user, 'userprofile', None) if hasattr(request, 'user') else None
    if config.get('company_required'):
        if not user_profile or not hasattr(user_profile, 'company'):
            return JsonResponse({'success': False, 'error': 'Company missing'}, status=403)

    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = min(max(1, int(request.GET.get('page_size', config.get('page_size', 50)))), 100)

    qs = model.objects.all()
    if config.get('company_required'):
        qs = qs.filter(company=user_profile.company)
    if config.get('filters'):
        qs = qs.filter(**config['filters'])
    if config.get('exclude'):
        qs = qs.exclude(**config['exclude'])

    if not query:
        qs = qs.order_by(config.get('default_order', 'pk'))
    else:
        # ===== ULTRA FAST PIPELINE EXECUTION =====
        final_qs = None
        best_rank = -1

        for pipeline in config.get('pipelines', []):
            if not pipeline['condition'](query):
                continue

            accumulated_qs = None
            for rule in pipeline['rules']:
                if 'if' in rule and not rule['if'](query):
                    continue

                temp_qs = _apply_lookup(qs, rule['field'], rule['lookup'], query)

                if temp_qs.exists(): # O(log n) check using index
                    if rule.get('stop_if_found'):
                        final_qs = temp_qs
                        best_rank = rule['rank']
                        break # STOP - exact found, don't do fuzzy
                    else:
                        if accumulated_qs is None:
                            accumulated_qs = temp_qs
                        else:
                            accumulated_qs = (accumulated_qs | temp_qs)

            if final_qs is not None: # stopped on exact
                break
            if accumulated_qs is not None:
                final_qs = accumulated_qs
                break

        if final_qs is None:
            final_qs = qs.none()

        qs = final_qs.distinct()

        # Add Google-like ranking
        rank_whens = []
        for pipeline in config.get('pipelines', []):
            if not pipeline['condition'](query): continue
            for rule in pipeline['rules']:
                if 'if' in rule and not rule['if'](query): continue
                if rule['lookup'] in ['exact', 'iexact']:
                    try:
                        val = int(query) if rule['field'] in ['inv_id','ACC_CODE'] and query.isdigit() else query
                        rank_whens.append(When(**{rule['field']: val, 'then': Value(rule['rank'])}))
                        rank_whens.append(When(**{f"{rule['field']}__iexact": query, 'then': Value(rule['rank'])}))
                    except:
                        pass

        if rank_whens:
            qs = qs.annotate(_rank=Case(*rank_whens, default=Value(0), output_field=IntegerField())).order_by('-_rank', config.get('default_order', 'pk'))
        else:
            qs = qs.order_by(config.get('default_order', 'pk'))

    paginator = Paginator(qs, page_size)
    page_obj = paginator.get_page(page)

    all_fields = list(dict.fromkeys(config.get('display_fields', []) + config.get('return_fields', [])))
    results = []
    for item in page_obj:
        row = {}
        for field in all_fields:
            if '__' in field:
                obj = item
                for part in field.split('__'):
                    obj = getattr(obj, part, None)
                    if obj is None: break
                row[field] = str(obj) if obj is not None else ''
            else:
                val = getattr(item, field, None)
                row[field] = float(val) if hasattr(val, 'as_integer_ratio') else (val if val is not None else '')
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