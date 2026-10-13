from django.test import TestCase

# Create your tests here.
import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.configuration.models import Branch, Company
from apps.inventory.models import Inventory, ItemCategory, ItemCompany, Unit
from apps.users.models import Permission, Role, UserProfile


class InventoryUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name='Test company')
        cls.branch = Branch.objects.create(name='Main', company=cls.company)
        cls.other_branch = Branch.objects.create(name='Other', company=cls.company)
        cls.other_company = Company.objects.create(name='Other company')
        cls.foreign_branch = Branch.objects.create(name='Foreign', company=cls.other_company)
        cls.role = Role.objects.create(name='Inventory editor', company=cls.company)
        for code in ('view_inventory', 'edit_item'):
            cls.role.permissions.add(Permission.objects.get_or_create(code=code, defaults={'name': code, 'module': 'inventory'})[0])
        cls.user = User.objects.create_user(username='editor', password='test-only')
        UserProfile.objects.create(user=cls.user, company=cls.company, branch=cls.branch, role=cls.role)
        cls.scope = {'company': cls.company, 'branch': cls.branch}
        cls.manufacturer = ItemCompany.objects.create(name='Acme', **cls.scope)
        cls.category = ItemCategory.objects.create(name='Food', **cls.scope)
        cls.unit = Unit.objects.create(name='Piece', **cls.scope)
        cls.item = Inventory.objects.create(prod_name='Apple', base_price='100.00', base_disc_per='10.00',
                                            manufacturer=cls.manufacturer, category=cls.category, bal_qty=25, **cls.scope)
        cls.second = Inventory.objects.create(prod_name='Banana', **cls.scope)
        cls.other = Inventory.objects.create(prod_name='Other branch item', company=cls.company, branch=cls.other_branch)
        cls.foreign = Inventory.objects.create(prod_name='Foreign item', company=cls.other_company, branch=cls.foreign_branch)
        cls.deleted = Inventory.objects.create(prod_name='Deleted', is_deleted=True, **cls.scope)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('inventory_update')

    def change(self, item=None, **values):
        item = item or self.item
        item.refresh_from_db()
        return {'id': item.pk, 'version': item.updated_at.isoformat(), 'values': values}

    def post(self, *changes, client=None):
        return (client or self.client).post(self.url, data=json.dumps({'changes': list(changes)}), content_type='application/json')

    def test_page_and_scope(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Formula studio')
        self.assertContains(response, 'Bulk Inventory Update')
        data = self.client.get(self.url, {'data': 1}).json()
        self.assertEqual({r['id'] for r in data['rows']}, {self.item.pk, self.second.pk})
        self.assertNotIn('cost', data['rows'][0])

    def test_filters(self):
        data = self.client.get(self.url, {'data': 1, 'manufacturer': self.manufacturer.pk,
                                         'category': self.category.pk, 'q': 'app'}).json()
        self.assertEqual([r['id'] for r in data['rows']], [self.item.pk])
        self.assertEqual(self.client.get(self.url, {'data': 1, 'category': 'bad'}).status_code, 400)

    def test_pagination(self):
        Inventory.objects.bulk_create([Inventory(prod_name=f'Product {i}', **self.scope) for i in range(102)])
        first = self.client.get(self.url, {'data': 1}).json()
        second = self.client.get(self.url, {'data': 1, 'page': 2}).json()
        self.assertEqual(len(first['rows']), 100)
        self.assertEqual(len(second['rows']), 4)
        self.assertFalse({r['id'] for r in first['rows']} & {r['id'] for r in second['rows']})

    def test_success_and_audit_without_stock_changes(self):
        change = self.change(base_price='125.50', carton_qty=12, base_uom=self.unit.pk,
                             active=False, expiry_date='2027-01-31', barcode='001234')
        response = self.post(change)
        self.assertEqual(response.status_code, 200, response.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.base_price, Decimal('125.50'))
        self.assertEqual(self.item.barcode, '001234')
        self.assertEqual(self.item.updated_by, 'editor')
        self.assertFalse(self.item.active)
        self.assertEqual(self.item.bal_qty, 25)
        self.assertNotEqual(change['version'], self.item.updated_at.isoformat())

    def test_atomic_validation(self):
        response = self.post(self.change(base_price='120.00'), self.change(self.second, ws_disc_per='101'))
        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.base_price, Decimal('100.00'))
        self.assertIn(str(self.second.pk), response.json()['errors'])

    def test_invalid_values(self):
        for values in ({'base_price': '-1'}, {'base_price': 'NaN'}, {'base_price': '1.234'},
                       {'base_price': '10000000000'}, {'carton_qty': 0}, {'dzn_qty': '1.5'},
                       {'min_stock': 10, 'max_stock': 5}, {'expiry_date': 'not-a-date'},
                       {'prod_name': ''}, {'barcode': 'x' * 256}):
            with self.subTest(values=values):
                self.assertEqual(self.post(self.change(**values)).status_code, 400)

    def test_unrelated_legacy_values_do_not_block_patch(self):
        # Existing zero pack sizes or retired classifications must not block a price-only edit.
        Inventory.objects.filter(pk=self.item.pk).update(carton_qty=0)
        response = self.post(self.change(base_price='150.00'))
        self.assertEqual(response.status_code, 200, response.content)
        self.item.refresh_from_db()
        self.assertEqual(self.item.carton_qty, 0)

    def test_clearing_optional_values(self):
        response = self.post(self.change(base_disc_per=None, category=None, active=None))
        self.assertEqual(response.status_code, 200, response.content)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.base_disc_per)
        self.assertIsNone(self.item.category_id)
        self.assertIsNone(self.item.active)

    def test_scope_and_protected_fields(self):
        for item in (self.other, self.foreign, self.deleted):
            self.assertEqual(self.post(self.change(item, base_price='50')).status_code, 400)
        for field in ('company', 'branch', 'bal_qty', 'updated_by', 'is_deleted', 'cost'):
            self.assertEqual(self.post(self.change(**{field: 1})).status_code, 400)
        foreign_unit = Unit.objects.create(name='Foreign unit', company=self.company, branch=self.other_branch)
        self.assertEqual(self.post(self.change(base_uom=foreign_unit.pk)).status_code, 400)

    def test_stale_version_rejects_whole_batch(self):
        stale = self.change(base_price='200')
        self.item.prod_name = 'Changed elsewhere'
        self.item.save()
        response = self.post(stale, self.change(self.second, base_price='300'))
        self.assertEqual(response.status_code, 409)
        self.second.refresh_from_db()
        self.assertIsNone(self.second.base_price)

    def test_malformed_payload(self):
        for body in ('not json', 'null', '[]', '{}', '{"changes": [null]}'):
            self.assertEqual(self.client.post(self.url, data=body, content_type='application/json').status_code, 400)
        change = self.change(base_price='10')
        self.assertEqual(self.post(change, change).status_code, 400)
        self.assertEqual(self.post(*[change] * 501).status_code, 400)

    def test_permissions_authentication_and_csrf(self):
        self.role.permissions.remove(Permission.objects.get(code='edit_item'))
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.post(self.change(base_price='10')).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(self.post(self.change(base_price='10'), client=client).status_code, 403)