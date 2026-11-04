import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from .schema import default_configuration_for
from .services.data_builders import build_voucher_data
from .services.renderer import DocumentRenderer
from .views import DocumentDataView


def voucher_rows(voucher_type="CP"):
    main_type, system_type = ("DR", "CR") if voucher_type in {"CP", "BP"} else ("CR", "DR")
    main_name = "Supplier A" if voucher_type in {"CP", "BP"} else "Customer A"
    common = {
        "V_TYPE": voucher_type,
        "VNO": 17,
        "AMOUNT": "1,250.00",
        "DESCRIPTION": "Voucher line",
        "COMPANY": None,
        "BRANCH": None,
        "DATE": "2026-11-04",
        "DATEENT": None,
        "USER": "admin",
        "POSTERMINAL": None,
        "REMARKS": "Test voucher",
    }
    return [
        SimpleNamespace(
            **common,
            ACC_CODE=200,
            REF_ACC_CODE=100,
            ACC_HEAD=main_name,
            AMT_TYPE=main_type,
            SHOW_IN_SALE_RPT="Y",
        ),
        SimpleNamespace(
            **common,
            ACC_CODE=100,
            REF_ACC_CODE=200,
            ACC_HEAD="Cash Account",
            AMT_TYPE=system_type,
            SHOW_IN_SALE_RPT="N",
        ),
    ]


ACCOUNT_MAP = {
    100: {"account_code": 100, "name": "Cash Account", "address": "", "phone": ""},
    200: {"account_code": 200, "name": "Account A", "address": "", "phone": ""},
}


class VoucherPrintTests(SimpleTestCase):
    def build_data(self, voucher_type="CP"):
        with patch(
            "apps.invoice_designer.services.data_builders._fetch_account_info_map",
            return_value=ACCOUNT_MAP,
        ):
            return build_voucher_data(voucher_rows(voucher_type))

    def test_dr_cr_totals_and_type_specific_party_fields(self):
        payment = self.build_data("CP")
        self.assertEqual(str(payment["totals"]["total_debit"]), "1250.00")
        self.assertEqual(str(payment["totals"]["total_credit"]), "1250.00")
        self.assertEqual(payment["voucher"]["paid_to"], "Supplier A")
        self.assertEqual(payment["voucher"]["paid_from"], "")
        self.assertEqual(payment["voucher"]["payment_account"], "Cash Account")

        receipt = self.build_data("CR")
        self.assertEqual(receipt["voucher"]["paid_from"], "Customer A")
        self.assertEqual(receipt["voucher"]["paid_to"], "")

    def test_voucher_row_filter_is_controllable(self):
        data = self.build_data()
        configuration = default_configuration_for("voucher", "a4")
        renderer = DocumentRenderer()

        main_html = renderer.render(configuration, data)
        self.assertIn("Paid To", main_html)
        self.assertIn("Supplier A", main_html)
        self.assertIn("Voucher Total", main_html)
        self.assertNotIn("doc-empty-row", main_html)

        configuration["sections"]["items"]["row_filter"] = "all"
        all_html = renderer.render(configuration, data)
        self.assertGreater(all_html.count("Voucher line"), main_html.count("Voucher line"))

        configuration["sections"]["items"]["row_filter"] = "system"
        system_html = renderer.render(configuration, data)
        self.assertIn("Cash Account", system_html)

    def test_every_voucher_page_type_has_professional_defaults(self):
        data = self.build_data()
        renderer = DocumentRenderer()
        for page_type in ("thermal_58", "thermal_80", "a5", "a4", "urdu_58mm", "urdu_80mm", "urdu_a5", "urdu_a4", "bilingual_80mm", "bilingual_a4"):
            with self.subTest(page_type=page_type):
                configuration = default_configuration_for("voucher", page_type)
                self.assertEqual(configuration["sections"]["items"]["row_filter"], "main")
                self.assertTrue(configuration["sections"]["items"]["table_borders"])
                customer_fields = configuration["sections"]["customer"]["fields"]
                self.assertIn("paid_to", {field["field"] for field in customer_fields})
                self.assertIn("paid_from", {field["field"] for field in customer_fields})
                html = renderer.render(configuration, data)
                self.assertIn("Supplier A", html)
                self.assertIn("Voucher line", html)
                self.assertNotIn("doc-empty-row", html)

    def test_document_data_endpoint_preserves_voucher_natural_key(self):
        request = RequestFactory().get("/invoice-designer/api/document-data/", {
            "document_type": "voucher",
            "model_name": "Gledg",
            "bill_number": "CP-17",
            "page_type": "a4",
        })
        view = DocumentDataView()
        builders = {"voucher": lambda row, include_previous_balance=False: {"items": [], "totals": {}}}
        with patch.object(view, "_load_header_row", return_value=[object()]) as load_row, \
                patch("apps.invoice_designer.views.DOCUMENT_DATA_BUILDERS", builders), \
                patch("apps.invoice_designer.views.TemplateConfiguration") as template:
            template.objects.filter.return_value.first.return_value = None
            response = view.get(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(load_row.call_args.args[2], "CP-17")
        self.assertEqual(json.loads(response.content)["document_data"], {"items": [], "totals": {}})
