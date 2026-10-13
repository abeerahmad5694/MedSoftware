"""
invoice_designer.models
------------------------
Deliberately minimal. The whole point of this app is that a printable
document is fully described by JSON configuration, not by database rows.
There is exactly one model that matters: TemplateConfiguration.

Everything else (Invoice, Purchase, Gledg, Company, ...) already exists
in the host ERP and is only ever *read* by this app through the data
builder functions in services/data_builders.py.
"""

from django.db import models

from .schema import default_configuration_for


class DocumentType(models.TextChoices):
    POS_INVOICE = "pos_invoice", "POS Invoice"
    PURCHASE_INVOICE = "purchase_invoice", "Purchase Invoice"
    CREDIT_SALE_INVOICE = "credit_sale_invoice", "Credit Sale Invoice"
    QUOTATION = "quotation", "Quotation"
    VOUCHER = "voucher", "Voucher"
    BARCODE_LABEL = "barcode_label", "Barcode Label"


class InvoiceLanguage(models.TextChoices):
    ENGLISH = "english", "English"
    URDU = "urdu", "Urdu"
    BILINGUAL = "bilingual", "Bilingual (English + Urdu)"


class PageType(models.TextChoices):
    THERMAL_58 = "thermal_58", "Thermal 58mm"
    THERMAL_80 = "thermal_80", "Thermal 80mm"
    A5 = "a5", "A5"
    A4 = "a4", "A4"
    # ---- Urdu page types (Nastaleeq / RTL) ----
    URDU_80MM = "urdu_80mm", "Thermal 80mm — Urdu"
    URDU_58MM = "urdu_58mm", "Thermal 58mm — Urdu"
    URDU_A4 = "urdu_a4", "A4 — Urdu"
    URDU_A5 = "urdu_a5", "A5 — Urdu"
    # ---- Bilingual page types (English + Urdu) ----
    BILINGUAL_A4 = "bilingual_a4", "A4 — Bilingual"
    BILINGUAL_80MM = "bilingual_80mm", "Thermal 80mm — Bilingual"


class TemplateConfiguration(models.Model):
    """
    One row = one editable design for (document_type, page_type).

    `configuration` is the single source of truth consumed by
    services.renderer.DocumentRenderer. It always follows the shape
    documented in schema.py, so the renderer never needs to guess.
    """

    document_type = models.CharField(max_length=32, choices=DocumentType.choices)
    page_type = models.CharField(max_length=16, choices=PageType.choices)

    is_enabled = models.BooleanField(
        default=True,
        help_text="Disabled page types are hidden from preview, print "
                   "selection and are never rendered.",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="The template used when no explicit template_id is given "
                   "for this document_type + page_type combination.",
    )

    name = models.CharField(max_length=120, default="Default")
    configuration = models.JSONField(default=dict, blank=True)

    # Language mode — controls which labels/names the renderer outputs.
    # Defaults to ENGLISH so existing templates are completely unaffected.
    invoice_language = models.CharField(
        max_length=16,
        choices=InvoiceLanguage.choices,
        default=InvoiceLanguage.ENGLISH,
        help_text="Choose Urdu or Bilingual to enable Nastaleeq font and RTL layout.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "page_type", "name"],
                name="unique_template_per_document_page_name",
            )
        ]
        ordering = ["document_type", "page_type", "-is_default", "name"]

    def __str__(self):
        return f"{self.get_document_type_display()} / {self.get_page_type_display()} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.configuration:
            self.configuration = default_configuration_for(self.document_type, self.page_type)
        super().save(*args, **kwargs)
