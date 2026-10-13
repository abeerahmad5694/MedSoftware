"""Tenant-scoped bulk maintenance of inventory master data (not stock movements)."""
import json
from decimal import Decimal

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import connections, transaction
from django.db.models import CharField, Q
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.inventory.models import Inventory
from apps.reports.services.urdu_names import glossary
from apps.myglobal.services.helpers import get_user_perms

GROUPS = {
    'Retail': ['base_price', 'base_disc_per', 'min_base_sale_price', 'base_uom'],
    'Wholesale': ['ws_price', 'ws_disc_per'],
    'Packing': ['carton_price', 'carton_qty', 'carton_disc_per', 'carton_uom',
                'dzn_price', 'dzn_qty', 'dzn_disc_per', 'dzn_uom'],
    'Details': ['prod_name', 'prod_name_ur', 'alias_name', 'manufacturer', 'category',
                'brand', 'subcategory', 'barcode', 'manualbc', 'barcode2', 'active'],
    'Stock limits': ['min_stock', 'max_stock', 'reorder', 'product_location', 'expiry_date'],
}
FIELDS = [name for fields in GROUPS.values() for name in fields]
RELATIONS = ['manufacturer', 'category', 'brand', 'subcategory', 'base_uom', 'carton_uom', 'dzn_uom']
LABELS = {
    'base_price': 'Retail / base price', 'base_disc_per': 'Retail discount %',
    'ws_price': 'Wholesale price', 'ws_disc_per': 'Wholesale discount %',
    'prod_name': 'Item name', 'prod_name_ur': 'Urdu name', 'manufacturer': 'Company / manufacturer',
    'manualbc': 'Manual barcode', 'dzn_price': 'Dozen price', 'dzn_qty': 'Dozen quantity',
    'dzn_uom': 'Dozen UOM', 'dzn_disc_per': 'Dozen discount %',
}


def scoped_form(scope):
    class BulkInventoryForm(forms.ModelForm):
        class Meta:
            model = Inventory
            fields = FIELDS

        def __init__(self, *args, **kwargs):
            edit_fields = kwargs.pop('edit_fields', None)
            super().__init__(*args, **kwargs)
            if edit_fields is not None:
                included = set(edit_fields)
                if included & {'min_stock', 'max_stock'}:
                    included.update({'min_stock', 'max_stock'})
                self.fields = {name: field for name, field in self.fields.items() if name in included}
            for name in RELATIONS:
                if name in self.fields:
                    self.fields[name].queryset = self.fields[name].queryset.filter(**scope)

        def clean(self):
            data = super().clean()
            for name, value in list(data.items()):
                if isinstance(value, (Decimal, int)) and not isinstance(value, bool) and name not in RELATIONS:
                    if value < 0:
                        self.add_error(name, 'Must be zero or greater.')
                    if name.endswith('_disc_per') and value > 100:
                        self.add_error(name, 'Discount must be between 0 and 100.')
                    if name in ('carton_qty', 'dzn_qty') and value == 0:
                        self.add_error(name, 'Pack quantity must be greater than zero, or blank.')
            if data.get('min_stock') is not None and data.get('max_stock') is not None:
                if data['min_stock'] > data['max_stock']:
                    self.add_error('max_stock', 'Maximum stock must be at least minimum stock.')
            return data
    return BulkInventoryForm


def serialize(item):
    data = {name: getattr(item, name + '_id' if name in RELATIONS else name) for name in FIELDS}
    data.update(id=item.pk, version=item.updated_at.isoformat(), updated_by=item.updated_by,
                bal_qty=item.bal_qty)
    return data


def schema(scope):
    form = scoped_form(scope)()
    result = []
    for group, names in GROUPS.items():
        for name in names:
            field = form.fields[name]
            kind = ('select' if name in RELATIONS else 'boolean' if name == 'active' else
                    'date' if isinstance(field, forms.DateField) else
                    'number' if isinstance(field, (forms.DecimalField, forms.IntegerField)) else 'text')
            result.append({'name': name, 'label': LABELS.get(name, name.replace('_', ' ').title()),
                           'group': group, 'type': kind,
                           'step': '0.01' if isinstance(field, forms.DecimalField) else '1',
                           'required': field.required,
                           'options': list(field.queryset.order_by('name').values('id', 'name')) if name in RELATIONS else []})
    return result


@login_required
@require_http_methods(['GET', 'POST'])
def inventory_update(request):
    try:
        profile = request.user.userprofile
        allowed = profile.role_id and all(get_user_perms(request, code)[0] for code in ('view_inventory', 'edit_item'))
        if not allowed or not profile.company_id or not profile.branch_id or profile.branch.company_id != profile.company_id:
            return JsonResponse({'error': 'Inventory view/edit permission and a valid company/branch are required.'}, status=403)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'A user profile is required.'}, status=403)
    scope = {'company_id': profile.company_id, 'branch_id': profile.branch_id}
    items = Inventory.objects.filter(**scope).exclude(is_deleted=True).order_by('inv_id')
    if request.method == 'POST':
        return save_changes(request, items, scope)
    if request.GET.get('data') == '1':
        for key in ('manufacturer', 'category'):
            value = request.GET.get(key)
            if value:
                if not value.isdigit():
                    return JsonResponse({'error': 'Invalid filter.'}, status=400)
                items = items.filter(**{key + '_id': int(value)})
        search = request.GET.get('q', '').strip()[:255]
        if search:
            items = items.filter(Q(prod_name__icontains=search) | Q(alias_name__icontains=search) |
                                 Q(barcode__icontains=search) | Q(manualbc__icontains=search) | Q(barcode2__icontains=search))
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except ValueError:
            return JsonResponse({'error': 'Invalid page.'}, status=400)
        count = items.count()
        page = min(page, max(1, (count + 99) // 100))
        rows = items.order_by('inv_id')[(page - 1) * 100:page * 100]
        return JsonResponse({'rows': [serialize(row) for row in rows], 'count': count, 'page': page, 'page_size': 100})
    return render(request, 'reports/inventory_update.html', {
        'editor_config': {'fields': schema(scope), 'urduGlossary': glossary(), 'storageKey': f'{request.user.pk}:{profile.company_id}:{profile.branch_id}'},
    })


def save_changes(request, items, scope):
    try:
        payload = json.loads(request.body)
        changes = payload.get('changes') if isinstance(payload, dict) else None
        if not isinstance(changes, list) or not 1 <= len(changes) <= 500:
            raise ValueError('Send between 1 and 500 changed items per save.')
        ids = []
        for change in changes:
            if not isinstance(change, dict) or type(change.get('id')) is not int:
                raise ValueError('Invalid item ID.')
            if not isinstance(change.get('values'), dict) or not change['values'] or set(change['values']) - set(FIELDS):
                raise ValueError('Invalid or protected fields in request.')
            if not isinstance(change.get('version'), str):
                raise ValueError('An item version is required.')
            for name, value in change['values'].items():
                if isinstance(value, (list, dict)) or (name == 'active' and value is not None and type(value) is not bool):
                    raise ValueError('Invalid field value.')
            ids.append(change['id'])
        if len(set(ids)) != len(ids):
            raise ValueError('Duplicate item IDs.')
    except (ValueError, UnicodeDecodeError) as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    # SQLite stores datetimes as text. Imported rows can contain a zero
    # fraction ('.000000'), which Django strips when preparing a DateTimeField
    # lookup. Capture and compare the exact stored text so the conditional
    # write does not falsely report a conflict for an unchanged timestamp.
    versioned_items = items
    version_field = 'updated_at'
    if connections[items.db].vendor == 'sqlite':
        version_field = '_stored_updated_at'
        versioned_items = items.annotate(
            _stored_updated_at=Cast('updated_at', output_field=CharField()),
        )

    with transaction.atomic(using=items.db):
        locked = {item.pk: item for item in versioned_items.select_for_update().filter(pk__in=ids).order_by('pk')}
        if len(locked) != len(ids):
            return JsonResponse({'error': 'One or more items are unavailable in your company/branch. Nothing saved.'}, status=400)
        conflicts = [c['id'] for c in changes if locked[c['id']].updated_at.isoformat() != c['version']]
        if conflicts:
            return JsonResponse({'error': 'Items changed since loading. Nothing saved. Review your changes, then discard/reload to get current values.', 'conflicts': conflicts}, status=409)
        prepared, errors = [], {}
        Form = scoped_form(scope)
        for change in changes:
            item = locked[change['id']]
            data = {name: getattr(item, name + '_id' if name in RELATIONS else name) for name in FIELDS}
            data.update(change['values'])
            form = Form(data, instance=item, edit_fields=change['values'])
            if not form.is_valid():
                errors[str(item.pk)] = form.errors.get_json_data()
            else:
                prepared.append((change, form.cleaned_data))
        if errors:
            return JsonResponse({'error': 'Validation failed. Nothing saved.', 'errors': errors}, status=400)
        for change, cleaned in prepared:
            values = {name: cleaned[name] for name in change['values']}
            values.update(updated_by=request.user.get_username(), updated_at=timezone.now())
            # Conditional write also guards backends where SELECT FOR UPDATE is unsupported.
            updated = versioned_items.filter(
                pk=change['id'],
                **{version_field: getattr(locked[change['id']], version_field)},
            ).update(**values)
            if updated != 1:
                transaction.set_rollback(True, using=items.db)
                return JsonResponse({'error': 'Concurrent update detected. Nothing saved; reload and retry.'}, status=409)
        return JsonResponse({'success': True, 'rows': [serialize(item) for item in items.filter(pk__in=ids)]})