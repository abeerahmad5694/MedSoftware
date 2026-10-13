from datetime import date, timedelta

from django.test import SimpleTestCase

from .views import _period_range, _valid_period


class DashboardPeriodTests(SimpleTestCase):
    def test_today_covers_only_the_current_date(self):
        today = date(2026, 9, 28)

        self.assertEqual(_period_range("today", today), (today, today))

    def test_seven_days_includes_today_and_the_previous_six_days(self):
        today = date(2026, 9, 28)

        self.assertEqual(
            _period_range("7_days", today),
            (today - timedelta(days=6), today),
        )

    def test_this_month_starts_on_the_first_day(self):
        today = date(2026, 9, 28)

        self.assertEqual(_period_range("this_month", today), (date(2026, 9, 1), today))

    def test_invalid_period_uses_a_valid_company_default(self):
        self.assertEqual(_valid_period("custom", "this_month"), "this_month")
        self.assertEqual(_valid_period("custom", "not-a-period"), "today")
