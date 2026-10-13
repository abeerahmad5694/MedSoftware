"""
invoice_designer.views
------------------------
Five endpoints, on purpose:

  DesignerView            GET  /designer/<document_type>/<page_type>/   -> the 3-panel editor
  ConfigurationView        GET  /api/configuration/                     -> load a template's JSON
                           POST /api/configuration/                     -> save a template's JSON
  RenderDocumentView       POST /api/render/                            -> Configuration + Data -> HTML
                                (the ONE renderer call. Preview and Print,
                                 local payload and server payload, all land here.)
  DocumentDataView         GET  /api/document-data/                     -> server-source document_data
  EnabledPageTypesView     GET  /api/page-types/<document_type>/        -> which page types to offer

No document-type-specific branching lives in the views — that all lives
in schema.py (defaults) and services/data_builders.py (server data).
"""

import json

from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
import uuid

from .models import DocumentType, PageType, TemplateConfiguration
from .schema import default_configuration_for, get_field_registry_payload
from .services.renderer import DocumentRenderer, TemplateConfigurationCache
from .services.data_builders import DOCUMENT_DATA_BUILDERS

renderer = DocumentRenderer()


def _parse_json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None


class DesignerView(View):
    """Renders the 3-panel designer shell. All actual editing happens
    client-side against the JSON API below — this view just bootstraps it."""

    def get(self, request, document_type="pos_invoice", page_type="thermal_80"):
        if document_type not in DocumentType.values:
            return HttpResponseBadRequest(f"Unknown document_type '{document_type}'")
        if page_type not in PageType.values:
            return HttpResponseBadRequest(f"Unknown page_type '{page_type}'")

        configuration = TemplateConfigurationCache.get_or_build(document_type, page_type)

        context = {
            "document_type": document_type,
            "page_type": page_type,
            "document_type_choices": DocumentType.choices,
            "page_type_choices": PageType.choices,
            "initial_configuration_json": json.dumps(configuration),
        }
        return render(request, "invoice_designer/designer.html", context)


@method_decorator(csrf_exempt, name="dispatch")  # host ERP should wire real CSRF/session auth
class ConfigurationView(View):
    def get(self, request):
        document_type = request.GET.get("document_type")
        page_type = request.GET.get("page_type")
        name = request.GET.get("name", "Default")

        if not document_type or not page_type:
            return HttpResponseBadRequest("document_type and page_type are required")

        configuration = TemplateConfigurationCache.get_or_build(document_type, page_type, name)
        template = TemplateConfiguration.objects.filter(
            document_type=document_type, page_type=page_type, name=name
        ).first()
        updated_at = template.updated_at.isoformat() if template and template.updated_at else None
        return JsonResponse({"configuration": configuration, "updated_at": updated_at})

    def post(self, request):
        body = _parse_json_body(request)
        if body is None:
            return HttpResponseBadRequest("Invalid JSON body")

        document_type = body.get("document_type")
        page_type = body.get("page_type")
        name = body.get("name", "Default")
        configuration = body.get("configuration")

        if not (document_type and page_type and configuration):
            return HttpResponseBadRequest("document_type, page_type and configuration are required")

        template, _created = TemplateConfiguration.objects.update_or_create(
            document_type=document_type,
            page_type=page_type,
            name=name,
            defaults={"configuration": configuration},
        )
        TemplateConfigurationCache.invalidate(document_type, page_type, name)

        return JsonResponse({"status": "saved", "id": template.id})


@method_decorator(csrf_exempt, name="dispatch")
class RenderDocumentView(View):
    """
    THE render endpoint. Both the live preview (fired on every property
    edit) and the print flow (DocumentPrinter.print) call this exact
    endpoint with exactly the same request shape:

        { "configuration": {...}, "document_data": {...} }

    It never queries a business model. Whether document_data was built
    from a database row (server data_source) or handed over as-is from
    a POS terminal (local data_source) is decided before this endpoint
    is called — see DocumentDataView for the "server" half of that.
    """

    def post(self, request):
        body = _parse_json_body(request)
        if body is None:
            return HttpResponseBadRequest("Invalid JSON body")

        configuration = body.get("configuration")
        document_data = body.get("document_data") or {}

        # User requested to print the payload in console
        # import json
        # print("\n=== INVOICE RENDER PAYLOAD (document_data) ===")
        # print(json.dumps(document_data, indent=2))
        # print("==============================================\n")

        if not configuration:
            return HttpResponseBadRequest("configuration is required")

        # 1. Fallback for company/branch if the POS payload provided empty strings.
        # This fixes "default company info is not showing only N/A".
        c_name = document_data.get("company", {}).get("name", "")
        if not c_name or not str(c_name).strip():
            try:
                from apps.configuration.models import Company, Branch
                from .services.data_builders import _company_and_branch_data
                c_data, b_data = _company_and_branch_data(Company.objects.first(), Branch.objects.first())
                document_data["company"] = c_data
                document_data["branch"] = b_data
            except Exception:
                pass

        # 2. Compute previous balance if the POS payload didn't provide it, 
        # but the template configuration wants to display it.
        totals_fields = configuration.get("sections", {}).get("totals", {}).get("fields", [])
        wants_prev_bal = any(f.get("field") == "previous_balance" and f.get("visible", True) for f in totals_fields)
        if wants_prev_bal:
            acc_code = document_data.get("customer", {}).get("account_code")
            if acc_code:
                from .services.ledger import get_previous_balance
                bill_no = document_data.get("bill_number")
                dateent = document_data.get("invoice_date")
                try:
                    prev_bal_data = get_previous_balance(bill_no, "pos_invoice", dateent, acc_code=acc_code)
                    if "totals" not in document_data:
                        document_data["totals"] = {}
                    document_data["totals"].update(prev_bal_data)
                    
                    # Recompute current balance too
                    totals = document_data["totals"]
                    from .services.data_builders import _number
                    received = _number(totals.get("cash_received")) + _number(totals.get("bank_received"))
                    totals["current_balance"] = round(
                        _number(totals.get("previous_balance")) + _number(totals.get("net_total")) - received, 
                        2
                    )
                except Exception:
                    pass

        html = renderer.render(configuration, document_data)
        return JsonResponse({"html": html})


class DocumentDataView(View):
    """
    Server data_source support. Given a document_type + a bill_number
    (or any natural key your ERP uses), looks up the model instance and
    runs it through the matching builder in services/data_builders.py.

    This is intentionally the ONLY place that touches Django models
    (Invoice, Purchase, Gledg, ...) — everything downstream only ever
    sees the unified document_data dict.
    """

    def get(self, request):
        document_type = request.GET.get("document_type")
        bill_number = request.GET.get("bill_number")
        model_name = request.GET.get("model_name")
        include_previous_balance = request.GET.get("show_previous_balance") == "true"

        if not (document_type and bill_number):
            return HttpResponseBadRequest("document_type and bill_number are required")

        builder = DOCUMENT_DATA_BUILDERS.get(document_type)
        if builder is None:
            return JsonResponse(
                {"error": f"No server data builder registered for '{document_type}' yet. "
                          f"Add one to services/data_builders.py."},
                status=501,
            )

        header_row = self._load_header_row(document_type, model_name, bill_number)
        if header_row is None:
            return JsonResponse({"error": f"{model_name or document_type} '{bill_number}' not found"}, status=404)

        document_data = builder(header_row, include_previous_balance=include_previous_balance)
        
        # Look up template configuration updated_at for cache validation
        page_type = request.GET.get("page_type")
        template_updated_at = None
        template_config = None
        if page_type:
            template = TemplateConfiguration.objects.filter(
                document_type=document_type, page_type=page_type, is_default=True
            ).first() or TemplateConfiguration.objects.filter(
                document_type=document_type, page_type=page_type
            ).first()
            if template:
                template_updated_at = template.updated_at.isoformat() if template.updated_at else None
                template_config = template.configuration
            else:
                template_config = default_configuration_for(document_type, page_type)

        company_updated_at = None
        branch_updated_at = None
        company_obj = getattr(header_row, "company", None)
        branch_obj = getattr(header_row, "branch", None)
        if company_obj and hasattr(company_obj, "updated_at") and company_obj.updated_at:
            company_updated_at = company_obj.updated_at.isoformat()
        if branch_obj and hasattr(branch_obj, "updated_at") and branch_obj.updated_at:
            branch_updated_at = branch_obj.updated_at.isoformat()

        return JsonResponse({
            "document_data": document_data,
            "template_updated_at": template_updated_at,
            "template_config": template_config,
            "company_updated_at": company_updated_at,
            "branch_updated_at": branch_updated_at,
        })

    # Model class lookup — maps model_name (from the client) to the
    # actual Django model. Add new models here as document types grow.
    MODEL_BY_NAME = None  # lazy-loaded to avoid app-registry races

    @classmethod
    def _get_model_map(cls):
        if cls.MODEL_BY_NAME is None:
            from apps.sale.models import Invoice
            from apps.purchase.models import Purchase
            from apps.quotation.models import Quotation
            from apps.myledger.models import Gledg
            cls.MODEL_BY_NAME = {
                "Invoice": Invoice,
                "Purchase": Purchase,
                "Quotation": Quotation,
                "Gledg": Gledg,
            }
        return cls.MODEL_BY_NAME

    def _load_header_row(self, document_type, model_name, bill_number):
        """
        Loads the is_header=True row for this bill_no from the real
        model. The real Invoice/Purchase/Quotation schema stores header + line
        items in the SAME table (see services/data_builders.py) so this
        is always a `filter(bill_no=..., is_header=True).first()` call,
        never a plain `.get(pk=...)`.

        For voucher document type, bill_number is in the format "CR-123"
        (v_type-vno) and we return a list of Gledg rows.
        """
        model_map = self._get_model_map()

        if document_type == "voucher":
            # bill_number expected as "CR-123" or just "123" with model_name as v_type
            from apps.myledger.models import Gledg
            if "-" in str(bill_number):
                v_type, vno = str(bill_number).rsplit("-", 1)
            else:
                v_type = model_name or "CR"
                vno = bill_number
            try:
                rows = list(Gledg.objects.filter(
                    V_TYPE=v_type.strip(), VNO=int(vno)
                ).select_related("COMPANY", "BRANCH").order_by("GLEDG_ID"))
                return rows if rows else None
            except Exception:
                return None

        if not model_name:
            doc_type_to_model = {
                "pos_invoice": "Invoice",
                "credit_sale_invoice": "Invoice",
                "purchase_invoice": "Purchase",
                "quotation": "Quotation",
            }
            model_name = doc_type_to_model.get(document_type)

        model = model_map.get(model_name)
        if model is None:
            return None
        try:
            return model.objects.filter(
                # bill_no=bill_number, is_header=True
                bill_no=bill_number
            ).select_related("company", "branch").first()
        except Exception:
            return None


class FieldRegistryView(View):
    """
    GET /api/field-registry/ -> the entire searchable field library
    (header/customer/footer fields, item columns, totals fields, style
    preset names). Pure Python data, never touches the database, so
    the designer can fetch it once and cache it in memory for the rest
    of the session (requirement #11 — no repeated registry lookups).
    """

    def get(self, request):
        response = JsonResponse(get_field_registry_payload())
        # Static for the lifetime of this deployment's code — safe for
        # the browser to cache aggressively between designer sessions.
        response["Cache-Control"] = "public, max-age=3600"
        return response


class EnabledPageTypesView(View):
    """Which page types should the print dialog / preview tab-bar offer
    for a given document_type. Disabled page types are filtered out here
    so the frontend never renders, fetches, or spends time on them."""

    def get(self, request, document_type):
        if document_type not in DocumentType.values:
            return HttpResponseBadRequest(f"Unknown document_type '{document_type}'")

        enabled = list(
            TemplateConfiguration.objects.filter(
                document_type=document_type, is_enabled=True
            ).values_list("page_type", flat=True).distinct()
        )

        if not enabled:
            # Nothing configured in the DB yet -> fall back to schema
            # defaults so the app is usable before any template is saved.
            enabled = [PageType.THERMAL_80, PageType.A4]

        return JsonResponse({"document_type": document_type, "enabled_page_types": enabled})


@method_decorator(csrf_exempt, name="dispatch")
class UploadImageView(View):
    """
    Endpoint for uploading custom logos and images from the designer.
    """
    def post(self, request):
        if 'image' not in request.FILES:
            return HttpResponseBadRequest("No image file provided")
            
        image_file = request.FILES['image']
        # Generate a unique filename to prevent collisions
        ext = image_file.name.split('.')[-1] if '.' in image_file.name else 'png'
        filename = f"invoice_designer/logos/{uuid.uuid4().hex}.{ext}"
        
        saved_path = default_storage.save(filename, image_file)
        file_url = default_storage.url(saved_path)
        
        return JsonResponse({"url": file_url})


class CompanyPreviewView(View):
    """
    Returns the first company + branch info so the designer can display
    the real company logo in the live preview without printing anything.
    Only ever called by the designer's JS — never during real rendering.
    """
    _cache = None  # module-level simple cache (refreshes on restart)

    def get(self, request):
        if CompanyPreviewView._cache is not None:
            return JsonResponse(CompanyPreviewView._cache)
        try:
            from apps.configuration.models import Company, Branch  # type: ignore
            company = Company.objects.first()
            branch = Branch.objects.first()
            from .services.data_builders import _logo_url
            result = {
                "company": {
                    "name": getattr(company, "name", ""),
                    "address": getattr(company, "address", ""),
                    "phone": getattr(company, "phone1", ""),
                    "email": getattr(company, "email", ""),
                    "license_number": getattr(company, "license_no", ""),
                    "logo_url": _logo_url(company),
                },
                "branch": {
                    "name": getattr(branch, "name", ""),
                    "address": getattr(branch, "address", ""),
                    "phone": getattr(branch, "phone1", ""),
                    "email": getattr(branch, "email", ""),
                    "license_number": getattr(branch, "license_no", ""),
                    "logo_url": _logo_url(branch),
                },
            }
            CompanyPreviewView._cache = result
            return JsonResponse(result)
        except Exception:
            return JsonResponse({"company": {}, "branch": {}})
