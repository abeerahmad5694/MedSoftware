from django.http import JsonResponse
from django.apps import apps
from django.db.models import Q, Value, Case, When, IntegerField
from django.core.paginator import Paginator
import re

SEARCH_REGISTRY = {
    'inventory.Inventory': {
        'primary_key': 'inv_id',
        'display_fields': ['inv_id', 'prod_name', 'barcode', 'base_price'],
        'display_headers': ['ID', 'Product Name', 'Barcode', 'Price'],
        'return_fields': ['inv_id', 'prod_name', 'base_price', 'barcode', 'alias_name', 'ws_price', 'carton_price', 'dzn_price', 'category__name'],
        'default_order': 'prod_name',
        'page_size': 50,
        'filters': {'is_deleted':False},
        'exclude': {},
        'company_required': True,
        "company_field" : 'company',
        'pipelines': [
            {
                'condition': lambda q: q.isdigit(),
                'rules': [
                    {'if': lambda q: len(q) <= 6, 'field': 'inv_id', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 5, 'field': 'barcode', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 5, 'field': 'barcode2', 'lookup': 'exact', 'rank': 95, 'stop_if_found': True},
                    {'if': lambda q: len(q) >= 5, 'field': 'manualbc', 'lookup': 'exact', 'rank': 90, 'stop_if_found': True},
                ]
            },
            {
                'condition': lambda q: not q.isdigit(),
                'rules': [
                    {'field': 'manualbc', 'lookup': 'iexact', 'rank': 100, 'stop_if_found': True},
                    {'field': 'barcode2', 'lookup': 'iexact', 'rank': 90, 'stop_if_found': True},
                    {'field': 'alias_name', 'lookup': 'iexact', 'rank': 80, 'stop_if_found': True},
                    {'field': 'barcode', 'lookup': 'iexact', 'rank': 70, 'stop_if_found': True},
                    # This is the fuzzy part - now tokenized
                    {'field': 'prod_name', 'lookup': 'token_and', 'rank': 50},
                    {'field': 'alias_name', 'lookup': 'token_and', 'rank': 40},
                ]
            }
        ]
    },
    'myaccounts.Accounts': {
        'primary_key': 'ACC_CODE',
        'display_fields': ['ACC_CODE','ACC_NAME','ADDRESS','PHONE_OFF'],
        'display_headers': ['ACC_CODE','ACC_NAME','ADDRESS','PHONE_OFF'],
        'return_fields': ['ACC_CODE','ACC_NAME','ADDRESS','PHONE_OFF'],
        'default_order': 'ACC_CODE',
        'page_size': 50,
        'filters': {'TYPE__exact': 'Detail'},
        'company_required': True,
        "company_field" : 'COMPANY',
        'pipelines': [
            {'condition': lambda q: True, 'rules': [
                {'field': 'ACC_CODE', 'lookup': 'exact', 'rank': 100, 'stop_if_found': True},
                {'field': 'ACC_NAME', 'lookup': 'token_and', 'rank': 50},
            ]}
        ]
    },
}

def tokenize_query(query):
    """wy+panel, 02=010=12 WAY PANEL -> ['wy','panel'] etc"""
    # replace all non-alphanumeric with space
    query = query.lower()
    query = re.sub(r'[^a-z0-9]+', ' ', query)
    tokens = [t for t in query.split() if t]
    return tokens

def build_token_q(field, tokens, lookup='icontains'):
    """
    Google type: ALL tokens must exist in field, but in any order
    wy panel -> prod_name contains wy AND contains panel
    """
    q = Q()
    for token in tokens:
        if len(token) <= 1:
            continue
        # For very short token like 'wy' -> allow fuzzy: w%y% inside word
        # This is what fixes WAY vs WY
        if len(token) <= 3:
            # Build regex-like via icontains for each char?
            # Simple fix: search token as is OR first char and last char
            # wy -> matches way because w and y both present close
            token_q = Q(**{f"{field}__icontains": token})
            # extra fuzzy for 2-3 char tokens: match if field contains first letter
            # This is why WAY PANEL will match wy panel
            if len(token) == 2:
                # wy -> w%y
                pattern = f"{token[0]}%{token[1]}"
                token_q |= Q(**{f"{field}__icontains": token[0]}) & Q(**{f"{field}__icontains": token[1]})
        else:
            token_q = Q(**{f"{field}__icontains": token})
        q &= token_q
    return q

def _apply_lookup(qs, field, lookup, query):
    if lookup == 'exact':
        try:
            if field in ['inv_id', 'ACC_CODE']:
                return qs.filter(**{field: int(query)})
        except ValueError:
            return qs.none()
        return qs.filter(**{field: query})
    elif lookup == 'iexact':
        return qs.filter(**{f"{field}__iexact": query})
    elif lookup == 'token_and':
        tokens = tokenize_query(query)
        if not tokens:
            return qs.none()
        token_q = build_token_q(field, tokens)
        return qs.filter(token_q)
    else:
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

    user_profile = getattr(request.user, 'userprofile', None) if hasattr(request, 'user') else None
    if config.get('company_required'):
        if not user_profile or not hasattr(user_profile, 'company'):
            return JsonResponse({'success': False, 'error': 'Company missing'}, status=403)

    query = request.GET.get('q', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = min(max(1, int(request.GET.get('page_size', config.get('page_size', 50)))), 100)

    qs = model.objects.all()
    company_field = config.get('company_field')
    if config.get('company_required') and company_field:
        qs = qs.filter(**{company_field: user_profile.company})
    if config.get('filters'): qs = qs.filter(**config['filters'])
    if config.get('exclude'): qs = qs.exclude(**config['exclude'])

    if not query:
        qs = qs.order_by(config.get('default_order', 'pk'))
    else:
        final_qs = None
        for pipeline in config.get('pipelines', []):
            if not pipeline['condition'](query): continue
            accumulated = None
            for rule in pipeline['rules']:
                if 'if' in rule and not rule['if'](query): continue
                temp_qs = _apply_lookup(qs, rule['field'], rule['lookup'], query)
                if temp_qs.exists():
                    if rule.get('stop_if_found'):
                        final_qs = temp_qs
                        break
                    else:
                        accumulated = temp_qs if accumulated is None else (accumulated | temp_qs)
            if final_qs is not None: break
            if accumulated is not None:
                final_qs = accumulated
                break

        qs = final_qs.distinct() if final_qs is not None else qs.none()
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
        'success': True, 'results': results, 'page': page_obj.number,
        'total_pages': paginator.num_pages, 'total_count': paginator.count,
        'display_headers': config.get('display_headers', all_fields),
        'display_fields': config.get('display_fields', all_fields),
    })