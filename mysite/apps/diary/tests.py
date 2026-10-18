from datetime import timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.configuration.models import Branch, Company
from apps.diary.models import DiaryHistory, DiaryItem
from apps.diary.services import apply_diary_action, soft_delete_diary_item
from apps.myaccounts.models import Accounts
from apps.users.models import Permission, Role, UserProfile


class DiaryReminderTests(TestCase):
    def make_receivable(self, **overrides):
        values = {
            "kind": DiaryItem.Kind.RECEIVABLE,
            "title": "Weekly collection",
            "acc_code": 12345,
            "scheduled_date": timezone.now().date(),
            "original_due_date": timezone.now().date(),
            "amount": Decimal("1000.00"),
            "remaining_amount": Decimal("1000.00"),
            "status": DiaryItem.Status.OPEN,
        }
        values.update(overrides)
        return DiaryItem.objects.create(**values)

    def test_partial_receipt_keeps_balance_and_logs_follow_up_date(self):
        item = self.make_receivable()
        next_date = timezone.now().date() + timedelta(days=4)

        apply_diary_action(
            item,
            {
                "action": "partial",
                "amount": "300.00",
                "next_date": next_date.isoformat(),
                "note": "First installment",
            },
        )

        item.refresh_from_db()
        self.assertEqual(item.status, DiaryItem.Status.OPEN)
        self.assertEqual(item.remaining_amount, Decimal("700.00"))
        self.assertEqual(item.scheduled_date, next_date)
        self.assertTrue(item.history.filter(action=DiaryHistory.Action.RECEIPT_PARTIAL).exists())
        self.assertTrue(item.history.filter(action=DiaryHistory.Action.EXTENDED).exists())

    def test_settlement_closes_balance_with_reason(self):
        item = self.make_receivable()

        apply_diary_action(
            item,
            {
                "action": "settle",
                "amount": "1000.00",
                "reason": "MUTUAL",
                "note": "Mutually adjusted against a return.",
            },
        )

        item.refresh_from_db()
        event = item.history.get(action=DiaryHistory.Action.SETTLED)
        self.assertEqual(item.status, DiaryItem.Status.SETTLED)
        self.assertEqual(item.remaining_amount, Decimal("0.00"))
        self.assertEqual(event.reason, DiaryHistory.SettlementReason.MUTUAL)

    def test_repeat_creates_next_occurrence_after_full_receipt(self):
        item = self.make_receivable(repeat_every_days=7)
        expected_date = timezone.now().date() + timedelta(days=7)

        apply_diary_action(item, {"action": "full"})

        next_item = DiaryItem.objects.exclude(pk=item.pk).get()
        self.assertEqual(next_item.kind, DiaryItem.Kind.RECEIVABLE)
        self.assertEqual(next_item.amount, Decimal("1000.00"))
        self.assertEqual(next_item.remaining_amount, Decimal("1000.00"))
        self.assertEqual(next_item.scheduled_date, expected_date)

    def test_delete_is_soft_and_preserves_history(self):
        item = self.make_receivable()
        history_before = item.history.count()

        soft_delete_diary_item(item, note="Wrong reminder")

        item.refresh_from_db()
        self.assertIsNotNone(item.deleted_at)
        self.assertEqual(item.status, DiaryItem.Status.CANCELLED)
        self.assertEqual(item.history.count(), history_before + 1)
        self.assertTrue(item.history.filter(action=DiaryHistory.Action.DELETED).exists())


@override_settings(ROOT_URLCONF="apps.diary.test_urls")
class DiaryModuleIntegrationTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Diary Integration Company")
        self.branch = Branch.objects.create(name="Diary Integration Branch", company=self.company)
        self.role = Role.objects.create(name="Diary Integration Role", company=self.company)
        self.role.permissions.set(
            Permission.objects.filter(
                code__in=[
                    "view_diary",
                    "create_diary_items",
                    "update_diary_items",
                    "delete_diary_items",
                    "add_payable_reminders",
                ]
            )
        )
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="diary-integration-user",
            password="test-password",
        )
        UserProfile.objects.create(
            user=self.user,
            role=self.role,
            company=self.company,
            branch=self.branch,
        )
        Accounts.objects.create(
            ACC_CODE=81234001,
            ACC_NAME="Diary Test Account",
            TYPE="Detail",
            COMPANY=self.company,
            BRANCH=self.branch,
        )
        self.client.force_login(self.user)

    def test_diary_page_renders(self):
        response = self.client.get("/diary/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diary")
        self.assertContains(response, "Today's due")

    def test_all_diary_date_range_filters_scheduled_dates_inclusively(self):
        selected_date = timezone.now().date()
        next_date = selected_date + timedelta(days=1)
        DiaryItem.objects.create(
            kind=DiaryItem.Kind.NOTE,
            title="Entry inside date range",
            scheduled_date=selected_date,
            company=self.company,
            branch=self.branch,
        )
        DiaryItem.objects.create(
            kind=DiaryItem.Kind.NOTE,
            title="Entry outside date range",
            scheduled_date=next_date,
            company=self.company,
            branch=self.branch,
        )

        response = self.client.get(
            "/diary/",
            {
                "view": "diary",
                "from_date": selected_date.isoformat(),
                "to_date": selected_date.isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entry inside date range")
        self.assertNotContains(response, "Entry outside date range")

    def test_create_payable_saves_account_code_without_account_relation(self):
        response = self.client.post(
            "/diary/api/items/",
            data=json.dumps({
                "kind": "PAYABLE",
                "title": "Supplier payment",
                "acc_code": 81234001,
                "scheduled_date": timezone.now().date().isoformat(),
                "amount": "1200.00",
                "repeat_every_days": "7",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        item = DiaryItem.objects.get(title="Supplier payment")
        self.assertEqual(item.acc_code, 81234001)
        self.assertEqual(item.remaining_amount, Decimal("1200.00"))
        self.assertEqual(item.repeat_every_days, 7)
        self.assertFalse(any(field.is_relation and field.name == "acc_code" for field in DiaryItem._meta.fields))
        self.assertEqual(item.history.get().dairyitem_id, item.pk)

    def test_receivable_create_permission_is_separate(self):
        response = self.client.post(
            "/diary/api/items/",
            data=json.dumps({
                "kind": "RECEIVABLE",
                "title": "Customer receipt",
                "acc_code": 81234001,
                "scheduled_date": timezone.now().date().isoformat(),
                "amount": "100.00",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
