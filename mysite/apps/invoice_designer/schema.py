"""
invoice_designer.schema
------------------------
The contract. Pure data, no DB access, no Django imports beyond what's
needed to describe shapes:

1. STYLE_PRESETS         — named style bundles (a field stores a preset
                           name + a small diff, never a full style object).
2. FIELD_REGISTRY         — searchable library for header / customer /
                           footer. Every entry with a `data_source` is
                           backed by a REAL column on Company, Branch,
                           POSTerminal or Invoice/Purchase (see the
                           model field map in each comment below).
                           Entries with `data_source: None` are
                           intentionally manual-entry-only — they never
                           pretend to pull from a database column that
                           doesn't exist (e.g. there's no Customer model
                           in this project, so "Customer Name" is typed
                           by the cashier, never invented).
3. ITEM_COLUMN_REGISTRIES — per document_type, because Invoice rows and
                           Purchase rows are genuinely different real
                           columns (no barcode/SKU/brand on either —
                           those were never real; batch/expiry only
                           exist on Purchase rows, not Invoice rows).
4. TOTALS_REGISTRY        — one shared registry, because data_builders.py
                           already normalizes Invoice's and Purchase's
                           differently-named header totals into the same
                           `totals.*` shape.
5. default_configuration_for(document_type, page_type) — the single
   place default field lists get built, document_type-aware for items.

Every list/dict operation in this module is O(n) in the number of
registry entries — no nested scans, no repeated full-registry rebuilds.
"""

from copy import deepcopy

# ---------------------------------------------------------------------------
# Physical page dimensions — sizes the live preview and the print stylesheet.
# ---------------------------------------------------------------------------
PAGE_DIMENSIONS_MILLIMETERS = {
    "thermal_58": {"width": 58, "height": None},   # None height = continuous roll
    "thermal_80": {"width": 80, "height": None},
    "a5": {"width": 148, "height": 210},
    "a4": {"width": 210, "height": 297},
    # Urdu / Bilingual page types (same physical sizes, RTL layout)
    "urdu_58mm": {"width": 58, "height": None},
    "urdu_80mm": {"width": 80, "height": None},
    "urdu_a4": {"width": 210, "height": 297},
    "urdu_a5": {"width": 148, "height": 210},
    "bilingual_a4": {"width": 210, "height": 297},
    "bilingual_80mm": {"width": 80, "height": None},
}

# ---------------------------------------------------------------------------
# 1. STYLE INHERITANCE — unchanged from the last pass, still the single
#    source of truth for how a preset + diff expands into real CSS.
# ---------------------------------------------------------------------------

DEFAULT_STYLE_BASE = {
    "font_family": "Arial",
    "font_size": 12,
    "bold": False,
    "italic": False,
    "underline": False,
    "alignment": "left",        # left | center | right
    "text_color": "#1a1a1a",
    "background_color": "transparent",
    "border": "none",
    "padding": "2px 0",
    "margin": "0",
    "width": "auto",
}

STYLE_PRESETS = {
    "normal": {},
    "small": {"font_size": 10},
    "muted_small": {"font_size": 10, "text_color": "#4a4a4a"},
    "heading": {"font_size": 16, "bold": True},
    "title": {"font_size": 14, "bold": True, "alignment": "center"},
    "bold_total": {"font_size": 14, "bold": True},
    "center": {"alignment": "center"},
    "center_small": {"font_size": 11, "alignment": "center"},
    "tiny": {"font_size": 8},
    "tiny_center": {"font_size": 8, "alignment": "center"},
    "logo": {"width": "70px"},
    # --- Urdu / Nastaleeq presets ---
    "urdu_normal": {"font_family": "Jameel Noori Nastaleeq", "alignment": "right"},
    "urdu_heading": {"font_family": "Jameel Noori Nastaleeq", "font_size": 18, "bold": True, "alignment": "center"},
    "urdu_title": {"font_family": "Jameel Noori Nastaleeq", "font_size": 16, "bold": True, "alignment": "center"},
    "urdu_small": {"font_family": "Jameel Noori Nastaleeq", "font_size": 10, "alignment": "right"},
    "urdu_tiny": {"font_family": "Jameel Noori Nastaleeq", "font_size": 8, "alignment": "right"},
    "urdu_bold_total": {"font_family": "Jameel Noori Nastaleeq", "font_size": 14, "bold": True, "alignment": "right"},
    "urdu_center_small": {"font_family": "Jameel Noori Nastaleeq", "font_size": 11, "alignment": "center"},
}


def resolve_style(style_name: str = "normal", overrides: dict = None) -> dict:
    merged = deepcopy(DEFAULT_STYLE_BASE)
    merged.update(STYLE_PRESETS.get(style_name, {}))
    if overrides:
        merged.update(overrides)
    return merged


def style_dict_to_css(style_dict: dict) -> str:
    """Complete style dict -> inline CSS string. O(1) — fixed number of
    known keys, never scales with document size."""
    if not style_dict:
        return ""
    declarations = []
    if style_dict.get("font_family"):
        declarations.append(f"font-family: {style_dict['font_family']};")
    if style_dict.get("font_size"):
        declarations.append(f"font-size: {style_dict['font_size']}px;")
    declarations.append("font-weight: bold;" if style_dict.get("bold") else "font-weight: normal;")
    if style_dict.get("italic"):
        declarations.append("font-style: italic;")
    if style_dict.get("underline"):
        declarations.append("text-decoration: underline;")
    if style_dict.get("alignment"):
        declarations.append(f"text-align: {style_dict['alignment']};")
    if style_dict.get("text_color"):
        declarations.append(f"color: {style_dict['text_color']};")
    if style_dict.get("background_color") and style_dict["background_color"] != "transparent":
        declarations.append(f"background-color: {style_dict['background_color']};")
    if style_dict.get("border") and style_dict["border"] != "none":
        declarations.append(f"border: {style_dict['border']};")
    if style_dict.get("padding"):
        declarations.append(f"padding: {style_dict['padding']};")
    if style_dict.get("margin"):
        declarations.append(f"margin: {style_dict['margin']};")
    if style_dict.get("width") and style_dict["width"] != "auto":
        declarations.append(f"width: {style_dict['width']};")
    return " ".join(declarations)


# ---------------------------------------------------------------------------
# 2. FIELD REGISTRY — header / customer / footer.
#
# data_source column legend (what real model.field backs each entry):
#   Company.name / .address / .phone1 / .email / .license_no / .logo
#   Branch.name  / .address / .phone1 / .email / .license_no / .logo
#   POSTerminal.name
#   Invoice.bill_no / .date / .salesman / .user / .header_remarks / .header_acc_code
#
# `data_source: None` = deliberately manual-entry-only. Nothing in this
# registry ever fabricates a value for a column that doesn't exist —
# there is no Customer model in this project, so customer_name/address/
# phone are typed by the cashier or left blank, never invented.
# ---------------------------------------------------------------------------

FIELD_REGISTRY = {
    # --- Header Fields (layout images + the document's own title) ---
    "company_logo": {
        "label": "Company Logo", "category": "Header Fields",
        "data_source": "company.logo_url", "field_type": "image",
        "default_visible": True, "default_style": "logo",
    },
    "branch_logo": {
        "label": "Branch Logo", "category": "Header Fields",
        "data_source": "branch.logo_url", "field_type": "image",
        "default_visible": False, "default_style": "logo",
    },
    "invoice_title": {
        "label": "Document Title", "category": "Header Fields",
        "data_source": "invoice_title", "field_type": "text",
        "default_visible": True, "default_style": "title",
    },

    # --- Company Fields (real: Company model) ---
    "company_name": {
        "label": "Company Name", "category": "Company Fields",
        "data_source": "company.name", "field_type": "text",
        "default_visible": True, "default_style": "heading",
    },
    "company_address": {
        "label": "Company Address", "category": "Company Fields",
        "data_source": "company.address", "field_type": "text",
        "default_visible": True, "default_style": "small",
    },
    "company_phone": {
        "label": "Company Phone", "category": "Company Fields",
        "data_source": "company.phone", "field_type": "text",
        "default_visible": True, "default_style": "small",
    },
    "company_email": {
        "label": "Company Email", "category": "Company Fields",
        "data_source": "company.email", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "company_license_number": {
        "label": "Company License Number", "category": "Company Fields",
        "data_source": "company.license_number", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },

    # --- Branch Fields (real: Branch model) ---
    "branch_name": {
        "label": "Branch Name", "category": "Branch Fields",
        "data_source": "branch.name", "field_type": "text",
        "default_visible": True, "default_style": "small",
    },
    "branch_address": {
        "label": "Branch Address", "category": "Branch Fields",
        "data_source": "branch.address", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "branch_phone": {
        "label": "Branch Phone", "category": "Branch Fields",
        "data_source": "branch.phone", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "branch_license_number": {
        "label": "Branch License Number", "category": "Branch Fields",
        "data_source": "branch.license_number", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },

    # --- Invoice Fields (real: Invoice header row + POSTerminal) ---
    "invoice_number": {
        "label": "Invoice Number", "category": "Invoice Fields",
        "data_source": "bill_number", "field_type": "text",
        "default_visible": True, "default_style": "normal",
    },
    "invoice_date": {
        "label": "Invoice Date", "category": "Invoice Fields",
        "data_source": "invoice_date", "field_type": "text",
        "default_visible": True, "default_style": "normal",
    },
    "salesman": {
        "label": "Salesman", "category": "Invoice Fields",
        "data_source": "salesman", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "cashier": {
        "label": "Cashier", "category": "Invoice Fields",
        "data_source": "cashier", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "terminal": {
        "label": "Terminal", "category": "Invoice Fields",
        "data_source": "terminal", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },

    # --- Customer Fields — sourced from Accounts table via _fetch_account_info().
    # ACC_CODE (PK) -> ACC_NAME, ADDRESS, MOBILE_NO. Single .only() query per render.
    "customer_account": {
        "label": "Customer Account Code", "category": "Customer Fields",
        "data_source": "customer.account_code", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "customer_name": {
        "label": "Customer Name", "category": "Customer Fields",
        "data_source": "customer.name", "field_type": "text",
        "default_visible": True, "default_style": "normal",
    },
    "customer_address": {
        "label": "Customer Address", "category": "Customer Fields",
        "data_source": "customer.address", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "customer_phone": {
        "label": "Customer Phone", "category": "Customer Fields",
        "data_source": "customer.phone", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },

    # --- Footer Fields (real: Invoice.header_remarks / .user, system clock) ---
    "remarks": {
        "label": "Remarks", "category": "Footer Fields",
        "data_source": "remarks", "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
    "thank_you_message": {
        "label": "Thank You Message", "category": "Footer Fields",
        "data_source": None, "field_type": "static_text",
        "default_visible": True, "default_style": "center_small",
        "static_text": "Thank you for your business!",
    },
    "terms_and_conditions": {
        "label": "Terms & Conditions", "category": "Footer Fields",
        "data_source": None, "field_type": "text",
        "default_visible": False, "default_style": "tiny",
    },
    "authorized_signature": {
        "label": "Authorized Signature", "category": "Footer Fields",
        "data_source": None, "field_type": "static_text",
        "default_visible": False, "default_style": "normal",
        "static_text": "Authorized Signature: ______________",
    },
    "powered_by": {
        "label": "Powered By Line", "category": "Footer Fields",
        "data_source": None, "field_type": "static_text",
        "default_visible": True, "default_style": "tiny_center",
        "static_text": "Powered by ERP Document Studio",
    },
    "printed_by": {
        "label": "Printed By", "category": "Footer Fields",
        "data_source": "printed_by", "field_type": "text",
        "default_visible": False, "default_style": "tiny",
    },
    "print_date": {
        "label": "Print Date", "category": "Footer Fields",
        "data_source": "print_date", "field_type": "text",
        "default_visible": True, "default_style": "tiny",
    },
    "print_time": {
        "label": "Print Time", "category": "Footer Fields",
        "data_source": "print_time", "field_type": "text",
        "default_visible": True, "default_style": "tiny",
    },

    # --- Custom Fields — always manual, always clearly optional extras ---
    "tagline": {
        "label": "Tagline", "category": "Custom Fields",
        "data_source": None, "field_type": "text",
        "default_visible": False, "default_style": "center_small",
    },
    "custom_heading": {
        "label": "Custom Heading", "category": "Custom Fields",
        "data_source": None, "field_type": "text",
        "default_visible": False, "default_style": "heading",
    },
    "custom_text": {
        "label": "Custom Text", "category": "Custom Fields",
        "data_source": None, "field_type": "text",
        "default_visible": False, "default_style": "small",
    },
}

# Which registry categories may be searched/added into each editable
# section. A field is never forced into a section — opt-in via (+).
SECTION_ALLOWED_CATEGORIES = {
    "header": ["Header Fields", "Company Fields", "Branch Fields", "Invoice Fields", "Custom Fields"],
    "customer": ["Customer Fields", "Custom Fields"],
    "footer": ["Footer Fields", "Custom Fields"],
}


# ---------------------------------------------------------------------------
# 3. ITEM COLUMN REGISTRIES — per document_type, real columns only.
#
# Sale row columns  <- Invoice model (is_header=False rows):
#   prod_name, category, qty, uom, packing_mode, pack_qty, rate,
#   row_discount_percent, row_discount_amount, row_net_total,
#   row_net_cost, row_rate_cost, row_notes
#
# Purchase row columns <- Purchase model (is_header=False rows):
#   same base set, plus row_batch_no, row_batch_qty, row_expiry_dt,
#   row_pack_qty_rcvd, row_trade_price, row_actual_retail_price,
#   row_oldcost, row_discount_percent2, row_discount_amount2,
#   row_bonus, row_bonus_amount, row_fc_rate, row_fc_amount,
#   row_total_cost_per_base_unit
# ---------------------------------------------------------------------------

_SHARED_ITEM_COLUMNS = {
    # format_key = short alias users type in format_string: {Product}, {Qty}, etc.
    # The internal key (e.g. product_name) always works too.
    "product_name": {"label": "Product",  "format_key": "Product",  "category": "Product",  "default_visible": True,  "default_width": "28%"},
    "category":     {"label": "Category", "format_key": "Category", "category": "Product",  "default_visible": False, "default_width": "12%"},
    "quantity":     {"label": "Qty",      "format_key": "Qty",      "category": "Quantity", "default_visible": True,  "default_width": "8%"},
    "unit":         {"label": "Unit",     "format_key": "Unit",     "category": "Quantity", "default_visible": False, "default_width": "8%"},
    "packing_mode": {"label": "Packing",  "format_key": "Packing",  "category": "Quantity", "default_visible": False, "default_width": "10%"},
    "pack_quantity":{"label": "Pack Qty", "format_key": "PackQty",  "category": "Quantity", "default_visible": False, "default_width": "8%"},
    "rate":         {"label": "Rate",     "format_key": "Rate",     "category": "Pricing",  "default_visible": True,  "default_width": "10%"},
    "discount_percent": {"label": "Disc. %", "format_key": "Disc",  "category": "Discount", "default_visible": False, "default_width": "7%"},
    "discount_amount":  {"label": "Disc.",   "format_key": "DiscAmt","category": "Discount", "default_visible": False, "default_width": "8%"},
    "item_notes":   {"label": "Notes",    "format_key": "Notes",    "category": "Extra",    "default_visible": False, "default_width": "15%"},
    "amount":       {"label": "Amount",   "format_key": "Amount",   "category": "Extra",    "default_visible": True,  "default_width": "12%"},
}

_SALE_ONLY_ITEM_COLUMNS = {
    "cost_price": {"label": "Cost Price", "format_key": "CostPrice", "category": "Pricing", "default_visible": False, "default_width": "10%"},
    "net_cost":   {"label": "Net Cost",   "format_key": "NetCost",   "category": "Pricing", "default_visible": False, "default_width": "10%"},
}

_PURCHASE_ONLY_ITEM_COLUMNS = {
    "batch_number":          {"label": "Batch No.",       "format_key": "Batch",      "category": "Inventory", "default_visible": False, "default_width": "10%"},
    "batch_quantity":        {"label": "Batch Qty",       "format_key": "BatchQty",   "category": "Inventory", "default_visible": False, "default_width": "8%"},
    "expiry_date":           {"label": "Expiry",          "format_key": "Expiry",     "category": "Inventory", "default_visible": False, "default_width": "10%"},
    "pack_quantity_received":{"label": "Qty Received",    "format_key": "QtyRcvd",    "category": "Inventory", "default_visible": False, "default_width": "10%"},
    "trade_price":           {"label": "Trade Price",     "format_key": "TradePrice", "category": "Pricing",  "default_visible": False, "default_width": "10%"},
    "retail_price":          {"label": "Retail Price",    "format_key": "RetailPrice","category": "Pricing",  "default_visible": False, "default_width": "10%"},
    "old_cost":              {"label": "Previous Cost",   "format_key": "OldCost",    "category": "Pricing",  "default_visible": False, "default_width": "10%"},
    "discount_percent_2":    {"label": "Disc. % (2nd)",   "format_key": "Disc2",      "category": "Discount", "default_visible": False, "default_width": "7%"},
    "discount_amount_2":     {"label": "Disc. (2nd)",     "format_key": "DiscAmt2",   "category": "Discount", "default_visible": False, "default_width": "8%"},
    "bonus_quantity":        {"label": "Bonus Qty",       "format_key": "BonusQty",   "category": "Extra",    "default_visible": False, "default_width": "8%"},
    "bonus_amount":          {"label": "Bonus Amount",    "format_key": "BonusAmt",   "category": "Extra",    "default_visible": False, "default_width": "10%"},
    "landed_cost":           {"label": "Landed Cost/Unit","format_key": "LandedCost", "category": "Pricing",  "default_visible": False, "default_width": "10%"},
}

_VOUCHER_ITEM_COLUMNS = {
    "account_code": {"label": "Account Code", "format_key": "AccCode", "category": "Account", "default_visible": False, "default_width": "15%"},
    "account_name": {"label": "Account Name", "format_key": "AccName", "category": "Account", "default_visible": True, "default_width": "30%"},
    "counter_account_code": {"label": "Counter Acc Code", "format_key": "CAccCode", "category": "Account", "default_visible": False, "default_width": "15%"},
    "counter_account_name": {"label": "Counter Acc Name", "format_key": "CAccName", "category": "Account", "default_visible": False, "default_width": "30%"},
    "description": {"label": "Description", "format_key": "Desc", "category": "Description", "default_visible": True, "default_width": "30%"},
    "debit_amount": {"label": "Debit", "format_key": "Debit", "category": "Amount", "default_visible": True, "default_width": "15%"},
    "credit_amount": {"label": "Credit", "format_key": "Credit", "category": "Amount", "default_visible": True, "default_width": "15%"},
}

ITEM_COLUMN_REGISTRIES = {
    "pos_invoice": {**_SHARED_ITEM_COLUMNS, **_SALE_ONLY_ITEM_COLUMNS},
    "credit_sale_invoice": {**_SHARED_ITEM_COLUMNS, **_SALE_ONLY_ITEM_COLUMNS},
    "purchase_invoice": {**_SHARED_ITEM_COLUMNS, **_PURCHASE_ONLY_ITEM_COLUMNS},
    "quotation": {**_SHARED_ITEM_COLUMNS, **_SALE_ONLY_ITEM_COLUMNS},
    "voucher": _VOUCHER_ITEM_COLUMNS,
}
# Renderer-side fallback lookup (label/width when a saved column config
# predates a registry change) — the union of every real column, so any
# document_type's saved config still resolves.
ITEM_COLUMN_REGISTRY = {**_SHARED_ITEM_COLUMNS, **_SALE_ONLY_ITEM_COLUMNS, **_PURCHASE_ONLY_ITEM_COLUMNS, **_VOUCHER_ITEM_COLUMNS}

DEFAULT_ITEM_COLUMN_KEYS = ["product_name", "quantity", "rate", "amount"]
DEFAULT_VOUCHER_COLUMN_KEYS = ["account_name", "description", "debit_amount", "credit_amount"]


def get_item_column_registry(document_type: str) -> dict:
    return ITEM_COLUMN_REGISTRIES.get(document_type, _SHARED_ITEM_COLUMNS)


# ---------------------------------------------------------------------------
# 4. TOTALS REGISTRY — shared, because data_builders.py already
#    normalizes Invoice's and Purchase's header totals (whatever their
#    real column names) into one `totals.*` shape. All backed by real
#    header_* columns except previous/current balance (from the Gledg
#    ledger service) and total_items (Invoice/Purchase.header_total_items).
# ---------------------------------------------------------------------------

TOTALS_REGISTRY = {
    "total_items": {"label": "Total Items", "data_source": "totals.total_items", "default_visible": False},
    "subtotal": {"label": "Sub Total", "data_source": "totals.subtotal", "default_visible": True},
    "discount": {"label": "Discount", "data_source": "totals.discount_amount", "default_visible": True},
    "gst": {"label": "GST", "data_source": "totals.gst_amount", "default_visible": False},
    "delivery_charges": {"label": "Delivery", "data_source": "totals.delivery_charges", "default_visible": False},
    "misc_charges": {"label": "Misc.", "data_source": "totals.misc_charges", "default_visible": False},
    "net_total": {"label": "Net Total", "data_source": "totals.net_total", "default_visible": True, "default_style": "bold_total"},
    "cash_received": {"label": "Cash Received", "data_source": "totals.cash_received", "default_visible": True},
    "bank_received": {"label": "Bank Received", "data_source": "totals.bank_received", "default_visible": False},
    "change_amount": {"label": "Change", "data_source": "totals.change_amount", "default_visible": True},
    "previous_balance": {"label": "Previous Balance", "data_source": "totals.previous_balance", "default_visible": False},
    "current_balance": {"label": "Current Balance", "data_source": "totals.current_balance", "default_visible": False},
}

DEFAULT_TOTALS_ORDER = [
    "subtotal", "discount", "gst", "delivery_charges", "misc_charges", "net_total",
    "previous_balance", "cash_received", "bank_received", "change_amount", "current_balance",
]


# ---------------------------------------------------------------------------
# helpers used by default_configuration_for()  — every loop below is O(n)
# in registry size, run once per fresh template, never per request.
# ---------------------------------------------------------------------------

def _field_entry(key: str) -> dict:
    entry = FIELD_REGISTRY[key]
    base = {
        "field": key,
        "visible": entry["default_visible"],
        "style": entry.get("default_style", "normal"),
        "prefix": "",
        "suffix": "",
    }
    if entry.get("field_type") == "image":
        base["logo_width"] = ""
        base["logo_height"] = ""
    return base


def _default_field_list(category_names):
    return [_field_entry(key) for key, entry in FIELD_REGISTRY.items() if entry["category"] in category_names]


def _default_header_fields():
    return _default_field_list(["Header Fields", "Company Fields", "Invoice Fields"])


def _default_customer_fields():
    return _default_field_list(["Customer Fields"])


def _default_footer_fields():
    return _default_field_list(["Footer Fields"])


def _default_item_columns(document_type: str):
    registry = get_item_column_registry(document_type)
    columns = []
    
    default_keys = DEFAULT_VOUCHER_COLUMN_KEYS if document_type == "voucher" else DEFAULT_ITEM_COLUMN_KEYS
    
    for order, key in enumerate(registry.keys(), start=1):
        entry = registry[key]
        is_default = key in default_keys
        columns.append({
            "field": key,
            "label": entry["label"],
            "visible": is_default,
            "order": default_keys.index(key) + 1 if is_default else order + len(default_keys),
            "width": entry["default_width"],
            "style": "normal",
            "format_string": "",      # e.g. "{product_name} ({discount_percent}%)"
            "always_show": False,     # if True, column never hidden even when all-zero
        })
    return columns


def _default_totals_fields():
    return [
        {
            "field": key,
            "visible": TOTALS_REGISTRY[key]["default_visible"],
            "order": order,
            "label": TOTALS_REGISTRY[key]["label"],
            "style": TOTALS_REGISTRY[key].get("default_style", "normal"),
            "hide_if_zero": True,   # renderer hides zero-valued rows by default
        }
        for order, key in enumerate(DEFAULT_TOTALS_ORDER, start=1)
    ]

# ---------------------------------------------------------------------------
# URDU COLUMN LABELS  — Nastaleeq translations for all item/totals/header
# labels. Stored in the configuration JSON under 'column_labels_ur' so the
# renderer can pass them to the template in one cheap key lookup.
# ---------------------------------------------------------------------------

URDU_COLUMN_LABELS = {
    # Item table headers
    "serial": "نمبر شمار",
    "product_name": "تفصیل",
    "category": "قسم",
    "description": "تفصیل",
    "quantity": "مقدار",
    "unit": "اکائی",
    "packing_mode": "پیکنگ",
    "pack_quantity": "پیک مقدار",
    "rate": "نرخ",
    "discount_percent": "رعایت %",
    "discount_amount": "رعایت",
    "item_notes": "نوٹس",
    "amount": "رقم",
    # Totals
    "total_items": "کل آئٹم",
    "subtotal": "ذیلی مجموع",
    "discount": "رعایت",
    "gst": "ٹیکس",
    "delivery_charges": "ڈیلیوری چارجز",
    "misc_charges": "متفرقہ چارجز",
    "net_total": "کل رقم",
    "cash_received": "نقد وصول شدہ",
    "bank_received": "بینک وصول شدہ",
    "change_amount": "واپسی",
    "previous_balance": "سابقہ بقایا",
    "current_balance": "موجودہ بقایا",
    # Header labels
    "invoice_number": "بل نمبر",
    "invoice_date": "تاریخ",
    "customer_name": "گاہک کا نام",
    "salesman": "سیلز مین",
    "cashier": "کیشیر",
    "thank_you_message": "شکریہ ، دوبارہ تشریف لائیں!",
    "grand_total": "میزان",
    "paid": "وصول شدہ",
    "balance": "بقایا",
}

# Page types that are Urdu-only (full RTL layout)
URDU_PAGE_TYPES = {"urdu_80mm", "urdu_58mm", "urdu_a4", "urdu_a5"}
# Page types that are bilingual (LTR + RTL columns)
BILINGUAL_PAGE_TYPES = {"bilingual_a4", "bilingual_80mm"}
# All page types that carry any Urdu content
URDU_CAPABLE_PAGE_TYPES = URDU_PAGE_TYPES | BILINGUAL_PAGE_TYPES


def is_urdu_page_type(page_type: str) -> bool:
    """True for pure-Urdu page types (RTL, Nastaleeq only)."""
    return page_type in URDU_PAGE_TYPES


def is_bilingual_page_type(page_type: str) -> bool:
    """True for bilingual page types (both LTR English and RTL Urdu)."""
    return page_type in BILINGUAL_PAGE_TYPES


def is_urdu_capable_page_type(page_type: str) -> bool:
    """True for any page type that includes Urdu text."""
    return page_type in URDU_CAPABLE_PAGE_TYPES


def get_invoice_language_for_page_type(page_type: str) -> str:
    """Returns the natural language for a page type ('english', 'urdu', 'bilingual')."""
    if page_type in URDU_PAGE_TYPES:
        return "urdu"
    if page_type in BILINGUAL_PAGE_TYPES:
        return "bilingual"
    return "english"



def default_configuration_for(document_type: str, page_type: str) -> dict:
    """The single place default values live. document_type-aware only
    for item columns (Invoice vs. Purchase real columns differ).
    Extended to include Urdu defaults for Urdu/Bilingual page types."""
    dimensions = PAGE_DIMENSIONS_MILLIMETERS.get(page_type, PAGE_DIMENSIONS_MILLIMETERS["a4"])
    invoice_language = get_invoice_language_for_page_type(page_type)
    is_urdu = is_urdu_page_type(page_type)
    is_bilingual = is_bilingual_page_type(page_type)

    # Pick default font based on languagef
    default_font = "Jameel Noori Nastaleeq" if is_urdu else "Arial"
    default_size = 14 if is_urdu else 12   # Nastaleeq needs slightly larger size for readability

    config = {
        "document_type": document_type,
        "page_type": page_type,
        "invoice_language": invoice_language,
        "page": {
            "width_mm": dimensions["width"],
            "height_mm": dimensions["height"],
            "margin_top_mm": 5, "margin_bottom_mm": 5,
            "margin_left_mm": 5, "margin_right_mm": 5,
        },
        "styles": {"default_font_family": default_font, "default_font_size": default_size},
        "sections": {
            "header": {"visible": True, "fields": _default_header_fields()},
            "customer": {"visible": True, "fields": _default_customer_fields(), "exclude_accounts": ""},
            "items": {"visible": True, "columns": _default_item_columns(document_type)},
            "totals": {"visible": True, "fields": _default_totals_fields()},
            "footer": {"visible": True, "fields": _default_footer_fields()},
        },
    }

    # Attach Urdu column labels for Urdu/Bilingual templates
    if is_urdu or is_bilingual:
        config["column_labels_ur"] = deepcopy(URDU_COLUMN_LABELS)

    return config


def get_field_registry_payload() -> dict:
    """Everything the designer's field libraries need, in one cheap,
    cacheable, DB-free payload — fetched once per session and cached
    client-side (O(1) after the first load)."""
    return {
        "fields": FIELD_REGISTRY,
        "section_categories": SECTION_ALLOWED_CATEGORIES,
        "item_columns_by_document_type": ITEM_COLUMN_REGISTRIES,
        "totals_fields": TOTALS_REGISTRY,
        "style_base": DEFAULT_STYLE_BASE,
        "style_presets": STYLE_PRESETS,
        "urdu_column_labels": URDU_COLUMN_LABELS,
        "urdu_page_types": list(URDU_PAGE_TYPES),
        "bilingual_page_types": list(BILINGUAL_PAGE_TYPES),
    }
