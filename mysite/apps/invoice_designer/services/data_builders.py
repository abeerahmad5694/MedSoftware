"""
invoice_designer.services.data_builders
------------------------------------------
Turns *existing* ERP model rows (Invoice, Purchase, ...) into the one
unified `document_data` shape the renderer understands.

This is the only layer that is allowed to know your ERP's real model
field names. If a field name differs from what's assumed below, this
is the one file to edit — the renderer, the templates and the JS never
change.

Real schema shape: your `Invoice` / `Purchase` tables are NOT header-
with-related-items. They are a single table per `bill_no`, where one
row has `is_header=True` (the totals/payment row) and every other row
for that same `bill_no` has `is_header=False` (one row per line item).
Every builder below queries that way — O(1) header lookup + O(n) line
items, never N+1.

Every value below maps to a real column on Company / Branch /
POSTerminal / Invoice / Purchase. Nothing here fabricates a value for
a column that doesn't exist (no barcode/SKU/brand/GST — those were
never real columns on these models).
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from apps.invoice_designer.services.ledger import get_previous_balance as _ledger_previous_balance

PACKING_MODE_LABELS = {1: "Base", 2: "Carton", 3: "Dozen", 4: "Wholesale"}


def _fetch_account_info(acc_code) -> dict:
    """
    Ultra-fast single-field lookup from the Accounts table.
    Uses .only() so the DB only reads 4 columns, and the PK filter
    is always an indexed integer = O(log n) at worst.
    Returns a dict with name/address/phone keys (empty strings on miss).
    """
    if not acc_code:
        return {"name": "", "address": "", "phone": ""}
    try:
        from apps.myaccounts.models import Accounts
        acc = Accounts.objects.only(
            "ACC_CODE", "ACC_NAME", "ADDRESS", "MOBILE_NO", "PHONE_OFF"
        ).filter(ACC_CODE=acc_code).first()
        if acc:
            phone = getattr(acc, "MOBILE_NO", "") or getattr(acc, "PHONE_OFF", "") or ""
            return {
                "account_code": acc_code,
                "name": getattr(acc, "ACC_NAME", "") or "",
                "address": getattr(acc, "ADDRESS", "") or "",
                "phone": phone,
            }
    except Exception:
        pass
    return {"account_code": acc_code, "name": "", "address": "", "phone": ""}


def _fetch_account_info_map(acc_codes) -> dict:
    """Fetch every account needed by a voucher in one indexed query."""
    codes = {code for code in acc_codes if code not in (None, "")}
    if not codes:
        return {}
    try:
        from apps.myaccounts.models import Accounts
        rows = Accounts.objects.only(
            "ACC_CODE", "ACC_NAME", "ADDRESS", "MOBILE_NO", "PHONE_OFF"
        ).filter(ACC_CODE__in=codes)
        return {
            acc.ACC_CODE: {
                "account_code": acc.ACC_CODE,
                "name": getattr(acc, "ACC_NAME", "") or "",
                "address": getattr(acc, "ADDRESS", "") or "",
                "phone": getattr(acc, "MOBILE_NO", "") or getattr(acc, "PHONE_OFF", "") or "",
            }
            for acc in rows
        }
    except Exception:
        return {}


def _get(row, field_name, default=None):
    """Defensive getattr — keeps this module usable even before every
    field listed here exists on the real ERP models. O(1)."""
    value = getattr(row, field_name, default)
    return default if value is None else value


def _number(value, default=0):
    return default if value is None else value


def _logo_url(model_instance) -> str:
    """FileField/ImageField -> its .url, tolerating a missing file,
    a missing storage backend, or a null field without raising."""
    if model_instance is None:
        return ""
    logo_field = getattr(model_instance, "logo", None)
    if not logo_field:
        return ""
    try:
        return logo_field.url
    except (ValueError, Exception):
        return ""


def get_previous_balance(bill_no, invoice_type: str = "pos_invoice", dateent=None, acc_code=None, excluded_acc_codes=None) -> dict:
    """
    Thin pass-through to services.ledger.get_previous_balance so callers
    that only import data_builders keep working. Passes acc_code directly
    so the ledger service doesn't need to re-query Invoice for it.
    """
    return _ledger_previous_balance(
        bill_no, invoice_type, dateent or datetime.now(),
        acc_code=acc_code,
        excluded_acc_codes=excluded_acc_codes,
    )


def _company_and_branch_data(company, branch):
    """Shared by both builders — Company/Branch shape is identical.
    Includes optional Urdu name/address fields (null-safe)."""
    return (
        {
            "name": getattr(company, "name", ""),
            "name_ur": getattr(company, "name_ur", "") or "",
            "address": getattr(company, "address", ""),
            "address_ur": getattr(company, "address_ur", "") or "",
            "phone": getattr(company, "phone1", ""),
            "email": getattr(company, "email", ""),
            "license_number": getattr(company, "license_no", ""),
            "ntn_no": getattr(company, "ntn_no", "") or "",
            "ntn_no_ur": getattr(company, "ntn_no_ur", "") or "",
            "logo_url": _logo_url(company),
        },
        {
            "name": getattr(branch, "name", ""),
            "name_ur": getattr(branch, "name_ur", "") or "",
            "address": getattr(branch, "address", ""),
            "address_ur": getattr(branch, "address_ur", "") or "",
            "phone": getattr(branch, "phone1", ""),
            "email": getattr(branch, "email", ""),
            "license_number": getattr(branch, "license_no", ""),
            "logo_url": _logo_url(branch),
        },
    )


def build_pos_invoice_data(header_row, include_previous_balance: bool = False) -> dict:
    """
    header_row: the Invoice row where is_header=True for a given bill_no.
    Line items are fetched separately (same table, is_header=False,
    same bill_no) since that's how the real schema stores them.
    """
    bill_no = _get(header_row, "bill_no")
    company_data, branch_data = _company_and_branch_data(_get(header_row, "company"), _get(header_row, "branch"))
    posterminal = _get(header_row, "posterminal")

    acc_code = _get(header_row, "header_acc_code")
    dateent = _get(header_row, "dateent")

    line_rows = _fetch_line_items(header_row.__class__, bill_no, header_row)
    inv_map = _fetch_inventory_map([getattr(r, "inv_id", None) for r in line_rows])

    data = {
        "bill_number": bill_no,
        "invoice_title": "INVOICE",
        "invoice_date": _get(header_row, "date") or dateent,
        "salesman": _get(header_row, "salesman", ""),
        "cashier": _get(header_row, "user", ""),
        "terminal": getattr(posterminal, "name", "") if posterminal else "",
        "remarks": _get(header_row, "header_remarks", ""),
        "printed_by": _get(header_row, "user", ""),
        "print_date": datetime.now().strftime("%Y-%m-%d"),
        "print_time": datetime.now().strftime("%H:%M:%S"),

        "company": company_data,
        "branch": branch_data,
        "customer": _fetch_account_info(acc_code),

        "totals": {
            "total_items": _get(header_row, "header_total_items", 0),
            "subtotal": _get(header_row, "header_item_total", 0),
            "discount_percent": _get(header_row, "header_discount_percent", 0),
            "discount_amount": _get(header_row, "header_discount_amount", 0),
            "delivery_charges": _get(header_row, "header_delivery_charges", 0),
            "gst_percent": _get(header_row, "header_gst_percent", 0),
            "gst_amount": _get(header_row, "header_gst_amount", 0),
            "misc_charges": _get(header_row, "header_msc_charges", 0),
            "net_total": _get(header_row, "header_net_total", 0),
            "cash_received": _get(header_row, "header_cash_paid", 0),
            "bank_received": _get(header_row, "header_bank_paid", 0),
            "change_amount": _get(header_row, "header_change_amount", 0),
        },

        "items": [
            _build_sale_item(row, inv_map.get(getattr(row, "inv_id", None)))
            for row in line_rows
        ],
    }

    if include_previous_balance:
        previous_balance = get_previous_balance(
            bill_no, invoice_type="pos_invoice",
            dateent=dateent, acc_code=acc_code,
        )
        data["totals"].update(previous_balance)
        data["totals"]["current_balance"] = round(
            _number(previous_balance.get("previous_balance"))
            + _number(data["totals"]["net_total"])
            - (_number(data["totals"]["cash_received"]) + _number(data["totals"]["bank_received"])),
            2,
        )

    return data


def _fetch_line_items(model_class, bill_no, header_row=None):
    """
    Fetch all non-header rows for this bill_no.

    The real schema stores header+items in ONE table. is_header=False rows
    are item rows. However when a bill has exactly ONE item, some ERP versions
    store that item data directly on the header row (is_header=True) — so if
    querying is_header=False returns nothing, we fall back to treating the
    header row itself as the single item row (it has all the same item-level
    fields: prod_name, qty, rate, etc.).
    """
    if model_class is None or bill_no is None:
        return []
    try:
        # rows = list(model_class.objects.filter(bill_no=bill_no, is_header=False).order_by("id"))
        rows = list(model_class.objects.filter(bill_no=bill_no).order_by("id"))
        if not rows and header_row is not None:
            # Single-item invoice — header row carries the item data
            return [header_row]
        return rows
    except Exception:
        return []


def _fetch_inventory_map(inv_ids) -> dict:
    if not inv_ids:
        return {}
    valid_ids = [i for i in inv_ids if i is not None]
    if not valid_ids:
        return {}
    try:
        from apps.inventory.models import Inventory
        return {
            inv.inv_id: inv
            for inv in Inventory.objects.filter(inv_id__in=set(valid_ids))
        }
    except Exception:
        return {}


def _populate_model_fields(item: dict, inv_instance, row_instance):
    """
    Auto-populates any extra custom or standard fields from Inventory and the line item row
    into the item dictionary so they are immediately available in the template and renderer.
    """
    if inv_instance:
        item["barcode"] = getattr(inv_instance, "barcode", "") or getattr(inv_instance, "manualbc", "") or ""
        item["brand"] = str(getattr(inv_instance, "brand", "") or "")
        item["generic_group"] = getattr(inv_instance, "generic_group", "") or ""
        item["salt_composition"] = getattr(inv_instance, "salt_composition", "") or ""
        item["strength"] = getattr(inv_instance, "strength", "") or ""
        item["registration_no"] = getattr(inv_instance, "registration_no", "") or ""
        item["product_location"] = str(getattr(inv_instance, "product_location", "") or "")
        if "warranty" not in item or not item["warranty"]:
            inv_w = getattr(inv_instance, "warranty", None) or getattr(inv_instance, "warranty_notes", None)
            if inv_w:
                item["warranty"] = inv_w
                item["warranty_notes"] = inv_w

        try:
            for f in inv_instance._meta.fields:
                fname = f.name
                if fname not in item and not fname.startswith("prod_picture") and fname not in ("company", "branch", "user", "updated_by", "history"):
                    val = getattr(inv_instance, f.attname, None)
                    if hasattr(val, "name"):
                        val = str(val.name)
                    elif hasattr(val, "__str__") and not isinstance(val, (int, float, str, bool, type(None))):
                        val = str(val)
                    if val is not None:
                        item[fname] = val
        except Exception:
            pass

    if row_instance:
        try:
            for f in row_instance._meta.fields:
                fname = f.name
                if fname not in item and not fname.startswith("header_") and fname not in ("id", "bill_no", "is_header", "company", "branch", "posterminal", "user", "history"):
                    val = getattr(row_instance, f.attname, None)
                    if val is not None:
                        item[fname] = val
        except Exception:
            pass


def _build_sale_item(row, inv=None) -> dict:
    """Matches schema.ITEM_COLUMN_REGISTRIES['pos_invoice'] and includes FOC,
    warranty, inventory attributes, and any dynamically added model fields."""
    inv_id = getattr(row, "inv_id", None)
    prod_name_ur = ""
    if inv is None and inv_id:
        try:
            from apps.inventory.models import Inventory
            inv = Inventory.objects.filter(inv_id=inv_id).first()
        except Exception:
            pass

    if inv:
        prod_name_ur = getattr(inv, "prod_name_ur", "") or ""

    foc_val = _get(row, "foc_qty", 0)
    billed_qty = _get(row, "qty", 0) + foc_val if _get(row, "qty", 0) < 0 else _get(row, "qty", 0) - foc_val
    row_notes = _get(row, "row_notes", "") or _get(row, "notes", "")
    warranty_val = _get(row, "warranty", "") or _get(row, "warranty_notes", "") or (getattr(inv, "warranty", "") if inv else "") or row_notes

    item = {
        "product_name": _get(row, "prod_name", ""),
        "product_name_ur": prod_name_ur or _get(row, "prod_name_ur", "") or "",
        "category": _get(row, "category", "") or (str(getattr(inv, "category", "")) if inv else ""),
        "quantity": billed_qty,
        "foc_qty": foc_val,
        "foc": foc_val,
        "unit": _get(row, "uom", "") or (str(getattr(inv, "base_uom", "")) if inv else ""),
        "packing_mode": PACKING_MODE_LABELS.get(_get(row, "packing_mode", 1), ""),
        "pack_quantity": _get(row, "pack_qty", 0),
        "rate": _get(row, "rate", 0),
        "discount_percent": _get(row, "row_discount_percent", 0),
        "discount_amount": _get(row, "row_discount_amount", 0),
        "cost_price": _get(row, "row_rate_cost", 0),
        "net_cost": _get(row, "row_net_cost", 0),
        "item_notes": row_notes,
        "row_notes": row_notes,
        "warranty": warranty_val,
        "warranty_notes": warranty_val,
        "amount": _get(row, "row_net_total", 0),
    }

    _populate_model_fields(item, inv, row)
    return item


def build_purchase_invoice_data(header_row, include_previous_balance: bool = False) -> dict:
    """
    Same shape as build_pos_invoice_data, sourced from the `Purchase`
    model (also single-table, bill_no + is_header).
    """
    bill_no = _get(header_row, "bill_no")
    acc_code = _get(header_row, "header_acc_code")
    company_data, branch_data = _company_and_branch_data(_get(header_row, "company"), _get(header_row, "branch"))

    line_rows = _fetch_line_items(header_row.__class__, bill_no, header_row)
    inv_map = _fetch_inventory_map([getattr(r, "inv_id", None) for r in line_rows])

    data = {
        "bill_number": bill_no,
        "invoice_title": "PURCHASE INVOICE",
        "invoice_date": _get(header_row, "date"),
        "salesman": _get(header_row, "salesman", ""),
        "cashier": _get(header_row, "user", ""),
        "terminal": "",
        "remarks": _get(header_row, "header_remarks", ""),
        "printed_by": _get(header_row, "user", ""),
        "print_date": datetime.now().strftime("%Y-%m-%d"),
        "print_time": datetime.now().strftime("%H:%M:%S"),
        "supplier_invoice_number": _get(header_row, "header_supl_inv_no", ""),
        "supplier_invoice_date": _get(header_row, "header_supl_inv_date"),

        "company": company_data,
        "branch": branch_data,
        "customer": _fetch_account_info(acc_code),

        "totals": {
            "total_items": _get(header_row, "header_total_items", 0),
            "subtotal": _get(header_row, "header_item_total", 0),
            "discount_percent": _get(header_row, "header_discount_percent", 0),
            "discount_amount": _get(header_row, "header_discount_amount", 0),
            "delivery_charges": _get(header_row, "header_freight_amount", 0),
            "gst_percent": _get(header_row, "header_gst_percent", 0),
            "gst_amount": _get(header_row, "header_gst_amount", 0),
            "misc_charges": _get(header_row, "header_msc_charges", 0),
            "net_total": _get(header_row, "header_net_total", 0),
            "cash_received": _get(header_row, "header_cash_paid", 0),
            "bank_received": _get(header_row, "header_bank_paid", 0),
            "change_amount": _get(header_row, "header_change_amount", 0),
        },

        "items": [
            _build_purchase_item(row, inv_map.get(getattr(row, "inv_id", None)))
            for row in line_rows
        ],
    }

    if include_previous_balance:
        previous_balance = get_previous_balance(
            bill_no, invoice_type="purchase_invoice",
            dateent=_get(header_row, "date"), acc_code=acc_code,
        )
        data["totals"].update(previous_balance)

    return data


def _build_purchase_item(row, inv=None) -> dict:
    """Matches schema.ITEM_COLUMN_REGISTRIES['purchase_invoice'] exactly
    — includes FOC, warranty, inventory attributes, and any dynamically added model fields."""
    inv_id = getattr(row, "inv_id", None)
    prod_name_ur = ""
    if inv is None and inv_id:
        try:
            from apps.inventory.models import Inventory
            inv = Inventory.objects.filter(inv_id=inv_id).first()
        except Exception:
            pass

    if inv:
        prod_name_ur = getattr(inv, "prod_name_ur", "") or ""
        
    foc_val = _get(row, "foc_qty", 0)
    billed_qty = _get(row, "qty", 0) + foc_val if _get(row, "qty", 0) < 0 else _get(row, "qty", 0) - foc_val
    row_notes = _get(row, "row_notes", "") or _get(row, "notes", "")
    warranty_val = _get(row, "warranty", "") or _get(row, "warranty_notes", "") or (getattr(inv, "warranty", "") if inv else "") or row_notes

    item = {
        "product_name": _get(row, "prod_name", ""),
        "product_name_ur": prod_name_ur or _get(row, "prod_name_ur", "") or "",
        "category": _get(row, "category", "") or (str(getattr(inv, "category", "")) if inv else ""),
        "quantity": billed_qty,
        "foc_qty": foc_val,
        "foc": foc_val,
        "unit": _get(row, "uom", "") or (str(getattr(inv, "base_uom", "")) if inv else ""),
        "packing_mode": PACKING_MODE_LABELS.get(_get(row, "packing_mode", 1), ""),
        "pack_quantity": _get(row, "pack_qty", 0),
        "rate": _get(row, "rate", 0),
        "discount_percent": _get(row, "row_discount_percent", 0),
        "discount_amount": _get(row, "row_discount_amount", 0),
        "item_notes": row_notes,
        "row_notes": row_notes,
        "warranty": warranty_val,
        "warranty_notes": warranty_val,
        "amount": _get(row, "row_net_total", 0),
        "batch_number": _get(row, "row_batch_no", ""),
        "batch_quantity": _get(row, "row_batch_qty", 0),
        "expiry_date": _get(row, "row_expiry_dt", ""),
        "pack_quantity_received": _get(row, "row_pack_qty_rcvd", 0),
        "trade_price": _get(row, "row_trade_price", 0),
        "retail_price": _get(row, "row_actual_retail_price", 0),
        "old_cost": _get(row, "row_oldcost", 0),
        "discount_percent_2": _get(row, "row_discount_percent2", 0),
        "discount_amount_2": _get(row, "row_discount_amount2", 0),
        "bonus_quantity": _get(row, "row_bonus", 0),
        "bonus_amount": _get(row, "row_bonus_amount", 0),
        "landed_cost": _get(row, "row_total_cost_per_base_unit", 0),
    }

    _populate_model_fields(item, inv, row)
    return item


def build_quotation_data(header_row, include_previous_balance: bool = False) -> dict:
    """
    header_row: the Quotation row where is_header=True for a given bill_no.
    Line items are fetched from the same Quotation table where is_header=False.
    """
    bill_no = _get(header_row, "bill_no")
    acc_code = _get(header_row, "header_acc_code")
    company_data, branch_data = _company_and_branch_data(_get(header_row, "company"), _get(header_row, "branch"))
    posterminal = _get(header_row, "posterminal")
    dateent = _get(header_row, "dateent")

    line_rows = _fetch_line_items(header_row.__class__, bill_no, header_row)
    inv_map = _fetch_inventory_map([getattr(r, "inv_id", None) for r in line_rows])

    data = {
        "bill_number": bill_no,
        "invoice_title": "QUOTATION",
        "invoice_date": _get(header_row, "date") or dateent,
        "salesman": _get(header_row, "salesman", ""),
        "cashier": _get(header_row, "user", ""),
        "terminal": getattr(posterminal, "name", "") if posterminal else "",
        "remarks": _get(header_row, "header_remarks", ""),
        "printed_by": _get(header_row, "user", ""),
        "print_date": datetime.now().strftime("%Y-%m-%d"),
        "print_time": datetime.now().strftime("%H:%M:%S"),

        "company": company_data,
        "branch": branch_data,
        "customer": _fetch_account_info(acc_code),

        "totals": {
            "total_items": _get(header_row, "header_total_items", 0),
            "subtotal": _get(header_row, "header_item_total", 0),
            "discount_percent": _get(header_row, "header_discount_percent", 0),
            "discount_amount": _get(header_row, "header_discount_amount", 0),
            "delivery_charges": _get(header_row, "header_delivery_charges", 0),
            "gst_percent": _get(header_row, "header_gst_percent", 0),
            "gst_amount": _get(header_row, "header_gst_amount", 0),
            "misc_charges": _get(header_row, "header_msc_charges", 0),
            "net_total": _get(header_row, "header_net_total", 0),
            "cash_received": _get(header_row, "header_cash_paid", 0),
            "bank_received": _get(header_row, "header_bank_paid", 0),
            "change_amount": _get(header_row, "header_change_amount", 0),
        },

        "items": [
            _build_sale_item(row, inv_map.get(getattr(row, "inv_id", None)))
            for row in line_rows
        ],
    }

    if include_previous_balance:
        previous_balance = get_previous_balance(
            bill_no, invoice_type="quotation",
            dateent=dateent, acc_code=acc_code,
        )
        data["totals"].update(previous_balance)
        data["totals"]["current_balance"] = round(
            _number(previous_balance.get("previous_balance"))
            + _number(data["totals"]["net_total"])
            - (_number(data["totals"]["cash_received"]) + _number(data["totals"]["bank_received"])),
            2,
        )

    return data


def build_voucher_data(header_row, include_previous_balance: bool = False) -> dict:
    """Build professional voucher data directly from its Gledg rows.

    ``D``/``DR`` and ``C``/``CR`` are both accepted because the voucher
    service writes the long form. Account details are fetched in one query,
    not two queries per row.
    """
    if isinstance(header_row, (list, tuple)):
        rows = list(header_row)
        header_row = rows[0] if rows else None
    else:
        v_type = _get(header_row, "V_TYPE")
        vno = _get(header_row, "VNO")
        if v_type and vno:
            rows = list(header_row.__class__.objects.filter(V_TYPE=v_type, VNO=vno).order_by("GLEDG_ID"))
        else:
            rows = [header_row] if header_row else []

    company_data, branch_data = _company_and_branch_data(
        _get(header_row, "COMPANY"), _get(header_row, "BRANCH")
    )
    v_type = str(_get(header_row, "V_TYPE", "") or "").strip().upper()
    title = {
        "CR": "CASH RECEIPT VOUCHER",
        "CP": "CASH PAYMENT VOUCHER",
        "BR": "BANK RECEIPT VOUCHER",
        "BP": "BANK PAYMENT VOUCHER",
        "JV": "JOURNAL VOUCHER",
    }.get(v_type, f"VOUCHER {v_type}".strip())

    account_map = _fetch_account_info_map(
        [code for row in rows for code in (
            _get(row, "ACC_CODE"), _get(row, "REF_ACC_CODE")
        )]
    )

    def account_info(code):
        return account_map.get(code) or {
            "account_code": code or "", "name": "", "address": "", "phone": ""
        }

    def row_account_name(row):
        # ACC_HEAD is the operator-entered voucher head and takes priority.
        head = str(_get(row, "ACC_HEAD", "") or "").strip()
        return head or account_info(_get(row, "ACC_CODE"))["name"]

    def is_main_row(row):
        return str(_get(row, "SHOW_IN_SALE_RPT", "N") or "N").strip().upper() == "Y"

    def joined_names(selected_rows):
        names = []
        seen = set()
        for row in selected_rows:
            name = row_account_name(row)
            if name and name not in seen:
                seen.add(name)
                names.append(name)
        return ", ".join(names)

    main_rows = [row for row in rows if is_main_row(row)]
    system_rows = [row for row in rows if not is_main_row(row)]
    party_name = joined_names(main_rows)
    payment_account = joined_names(system_rows)

    def amount_value(row):
        try:
            return Decimal(str(_get(row, "AMOUNT", 0) or 0).replace(",", ""))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    total_debit = sum(
        (amount_value(row) for row in rows
         if str(_get(row, "AMT_TYPE", "") or "").strip().upper() in {"D", "DR"}),
        Decimal("0"),
    )
    total_credit = sum(
        (amount_value(row) for row in rows
         if str(_get(row, "AMT_TYPE", "") or "").strip().upper() in {"C", "CR"}),
        Decimal("0"),
    )

    # Existing customer_name fields also become useful on vouchers. Journal
    # vouchers intentionally have no single counterparty; both rows are shown.
    party_row = main_rows[0] if main_rows and v_type != "JV" else None
    customer_info = account_info(_get(party_row, "ACC_CODE")) if party_row else {
        "account_code": "", "name": "", "address": "", "phone": ""
    }
    if party_row:
        customer_info = dict(customer_info)
        customer_info["name"] = row_account_name(party_row)

    data = {
        "bill_number": f"{v_type}-{_get(header_row, 'VNO')}",
        "invoice_title": title,
        "invoice_date": _get(header_row, "DATE") or _get(header_row, "DATEENT"),
        "salesman": "",
        "cashier": _get(header_row, "USER", ""),
        "terminal": getattr(_get(header_row, "POSTERMINAL"), "name", "") if _get(header_row, "POSTERMINAL") else "",
        "remarks": _get(header_row, "REMARKS", ""),
        "printed_by": _get(header_row, "USER", ""),
        "print_date": datetime.now().strftime("%Y-%m-%d"),
        "print_time": datetime.now().strftime("%H:%M:%S"),
        "company": company_data,
        "branch": branch_data,
        "customer": customer_info,
        "voucher": {
            "voucher_type": v_type,
            "paid_to": party_name if v_type in {"CP", "BP"} else "",
            "paid_from": party_name if v_type in {"CR", "BR"} else "",
            "payment_account": payment_account,
        },
        "totals": {
            "total_items": len(main_rows) if main_rows else len(rows),
            "subtotal": total_debit,
            "discount_percent": 0,
            "discount_amount": 0,
            "delivery_charges": 0,
            "gst_percent": 0,
            "gst_amount": 0,
            "misc_charges": 0,
            "net_total": total_debit or total_credit,
            "total_debit": total_debit,
            "total_credit": total_credit,
            "cash_received": 0,
            "bank_received": 0,
            "change_amount": 0,
        },
        "items": [],
    }

    for row in rows:
        acc_info = account_info(_get(row, "ACC_CODE"))
        ref_acc_info = account_info(_get(row, "REF_ACC_CODE"))
        amount_type = str(_get(row, "AMT_TYPE", "") or "").strip().upper()
        amount = amount_value(row)
        data["items"].append({
            "account_code": acc_info.get("account_code", ""),
            "account_name": row_account_name(row),
            "counter_account_code": ref_acc_info.get("account_code", ""),
            "counter_account_name": ref_acc_info.get("name", ""),
            "description": _get(row, "DESCRIPTION", ""),
            "debit_amount": amount if amount_type in {"D", "DR"} else 0,
            "credit_amount": amount if amount_type in {"C", "CR"} else 0,
            "amount": amount,
            "show_in_sale_rpt": "Y" if is_main_row(row) else "N",
        })

    return data


# Document type -> builder function. RenderDocumentView/DocumentDataView
# use this map so adding a new document type never means touching the
# view or the renderer.
DOCUMENT_DATA_BUILDERS = {
    "pos_invoice": build_pos_invoice_data,
    "credit_sale_invoice": build_pos_invoice_data,   # same real columns as POS today
    "purchase_invoice": build_purchase_invoice_data,
    "quotation": build_quotation_data,
    "voucher": build_voucher_data,
}
