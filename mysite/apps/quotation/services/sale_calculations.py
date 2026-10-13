
from decimal import Decimal


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

    total_paid = Decimal(int(cash_paid) + int(bank_paid))

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



from apps.inventory.models import Inventory

def calculate_cost(inv_id,qty):
    last_pur_price, cost = Inventory.objects.filter(
        inv_id=inv_id
        ).values_list(
            'last_pur_price',
            'cost'
        ).get()

    cost = last_pur_price if cost<=1 else cost
    return cost    