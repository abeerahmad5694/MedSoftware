# helpers.py
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
import pytz #type:ignore
from decimal import Decimal
from apps.sale.models import Invoice
from datetime import timedelta 
import datetime

karachi_tz = pytz.timezone('Asia/Karachi')

from django.db import connection

# def get_next_bill_no(vtype):
#     with connection.cursor() as cursor:
#         cursor.execute("SELECT retvchno(%s);", [vtype])
#         new_bill_no = cursor.fetchone()[0]
        
#     return new_bill_no




# -----------------------------

def now_karachi():
    return timezone.now()
    # return timezone.now() + timedelta(hours=5)

def calculate_row_totals(item):
    """
    Calculate a single invoice row.
    """

    qty = Decimal(str(item.get("qty", 0)))
    rate = Decimal(str(item.get("rate", 0)))

    gross_total = qty * rate

    discount_percent = Decimal(
        str(item.get("row_discount_percent", 0))
    )

    discount_amount = Decimal(
        str(item.get("row_discount_amount", 0))
    )

    # Calculate amount from percent if amount not supplied
    if discount_amount == 0 and discount_percent > 0:
        discount_amount = (
            gross_total * discount_percent
        ) / Decimal("100")

    net_total = gross_total - discount_amount

    return {
        "qty": qty,
        "rate": rate,
        "row_discount_percent": discount_percent,
        "row_discount_amount": discount_amount,
        "row_net_total": net_total,
    }

def calculate_header_totals(header_fields, items):
    """
    Calculate invoice header totals from detail rows.
    """

    item_total = Decimal("0")

    for item in items:
        row = calculate_row_totals(item)
        item_total += row["row_net_total"]

    total_items = len(items)

    discount_percent = Decimal(
        str(header_fields.get("header_discount_percent", 0))
    )

    discount_amount = Decimal(
        str(header_fields.get("header_discount_amount", 0))
    )

    if discount_amount == 0 and discount_percent > 0:
        discount_amount = (
            item_total * discount_percent
        ) / Decimal("100")

    delivery_charges = Decimal(
        str(header_fields.get("header_delivery_charges", 0))
    )

    gst_percent = Decimal(
        str(header_fields.get("header_gst_percent", 0))
    )

    taxable_amount = (
        item_total
        - discount_amount
        + delivery_charges
    )

    gst_amount = Decimal(
        str(header_fields.get("header_gst_amount", 0))
    )

    if gst_amount == 0 and gst_percent > 0:
        gst_amount = (
            taxable_amount * gst_percent
        ) / Decimal("100")

    msc_charges = Decimal(
        str(header_fields.get("header_msc_charges", 0))
    )

    net_total = (
        taxable_amount
        + gst_amount
        + msc_charges
    )

    cash_paid = Decimal(
        str(header_fields.get("header_cash_paid", 0))
    )

    bank_paid = Decimal(
        str(header_fields.get("header_bank_paid", 0))
    )

    total_paid = cash_paid + bank_paid

    change_amount = max(
        Decimal("0"),
        total_paid - net_total
    )

    return {
        "header_total_items": total_items,
        "header_item_total": item_total,
        "header_discount_percent": discount_percent,
        "header_discount_amount": discount_amount,
        "header_delivery_charges": delivery_charges,
        "header_gst_percent": gst_percent,
        "header_gst_amount": gst_amount,
        "header_msc_charges": msc_charges,
        "header_net_total": net_total,
        "header_cash_paid": cash_paid,
        "header_bank_paid": bank_paid,
        "header_total_paid": total_paid,
        "header_change_amount": change_amount,
    }

def json_to_invoice(
    item=None,
    header_fields=None,
    fields_will_update=None,
    system_fields=None,
    is_header=False,
    update=False):
    item = item or {}
    header_fields = header_fields or {}
    fields_will_update = fields_will_update or {}
    system_fields = system_fields or {}

    row_data = calculate_row_totals(item)

    invoice_data = {
        # common
        "bill_no": fields_will_update.get("bill_no"),
        "is_header": is_header,

        "date": header_fields.get("date"),
        "dateent": fields_will_update.get("dateent"),
        "dateedit": now_karachi() if update else None,

        "user": fields_will_update.get("user", ""),
        "edit_by": system_fields.get("user", "") if update else None,
        "header_edit_count": fields_will_update.get(
            "header_edit_count", 0
        ) if update else 0,
        

        "company": system_fields.get("company"),
        "branch": system_fields.get("branch"),
        "posterminal": system_fields.get("posterminal"),

        # detail row fields
        "inv_id": item.get("inv_id"),
        "prod_name": item.get("prod_name", ""),
        "category": item.get("category", ""),

        "qty": row_data["qty"],
        "rate": row_data["rate"],

        "packing_mode": item.get(
            "packing_mode", 1
        ),
        "uom":item.get('uom',None),

        "pack_qty": Decimal(
            str(item.get("pack_qty", 0))
        ),

        "row_discount_percent":
            row_data["row_discount_percent"],

        "row_discount_amount":
            row_data["row_discount_amount"],

        "row_net_total":
            row_data["row_net_total"],

        "row_notes":
            item.get("row_notes", ""),
    }

    if is_header:
        header_copy = header_fields.copy()
        header_copy.pop("items", None)
        invoice_data.update(header_copy)

    return Invoice(**invoice_data)
