
from decimal import Decimal



from decimal import Decimal, ROUND_HALF_UP


D = lambda v: Decimal(str(v or 0))

def calculate_purchase_row(item):
    billed_qty = D(item.get("qty"))              # Billed / paid packs entered in UI
    foc = D(item.get("foc_qty") or item.get("foc", 0))  # FOC packs (Free of Cost)
    rate = D(item.get("rate"))                   # Rate per PACK if mode 2,3, else per base unit
    packing_mode = int(item.get("packing_mode", 1))
    pack_qty = D(item.get("pack_qty", 1)) or Decimal('1')
    bonus = D(item.get("row_bonus", 0))          # Bonus always in BASE units

    # Handle signs for purchase returns (negative billed_qty)
    if billed_qty < 0:
        foc_qty = -abs(foc) if foc != 0 else Decimal('0')
        total_qty = billed_qty + foc_qty
    else:
        foc_qty = abs(foc)
        total_qty = billed_qty + foc_qty

    # 1. Base quantities conversion with uniform packing logic for both billed qty and FOC
    if packing_mode in [2, 3]:  # carton / dozen
        pack_multiplier = pack_qty
    else:
        pack_multiplier = Decimal('1')
        pack_qty = Decimal('1')  # normalize

    billed_base_qty = billed_qty * pack_multiplier
    foc_base_qty = foc_qty * pack_multiplier
    base_qty = total_qty * pack_multiplier

    # 2. Gross — calculated on BILLED (paid) packs only; FOC is free
    gross = billed_qty * rate

    # 3. Discounts (applied on billed gross)
    disc1_p = D(item.get("row_discount_percent"))
    disc1_a = D(item.get("row_discount_amount"))
    if disc1_a == 0 and disc1_p > 0:
        disc1_a = gross * disc1_p / Decimal('100')

    disc2_p = D(item.get("row_discount_percent2", 0))
    disc2_a = D(item.get("row_discount_amount2", 0))
    if disc2_a == 0 and disc2_p > 0:
        disc2_a = (gross - disc1_a) * disc2_p / Decimal('100')

    net_total = gross - disc1_a - disc2_a

    # 4. Effective base qty for COSTING denominator:
    #    Landed purchase cost is spread over all base units entering inventory (billed + FOC + bonus).
    eff_base_qty = base_qty + (bonus if billed_qty >= 0 else -abs(bonus))

    return {
        "qty": total_qty,               # total packs stored in DB (billed + FOC)
        "foc_qty": abs(foc_qty),        # FOC packs stored in DB
        "billed_qty": billed_qty,       # paid packs (invoice qty)
        "base_qty": base_qty,           # total base units for STOCK (incl. FOC)
        "foc_base_qty": foc_base_qty,   # FOC base units
        "billed_base_qty": billed_base_qty,
        "eff_base_qty": eff_base_qty,   # costing denominator
        "rate": rate,
        "pack_qty": pack_qty,
        "packing_mode": packing_mode,
        "bonus": bonus,
        "gross_total": gross,
        "row_discount_percent": disc1_p,
        "row_discount_amount": disc1_a,
        "row_discount_percent2": disc2_p,
        "row_discount_amount2": disc2_a,
        "row_net_total": net_total,
    }

def calculate_landed_cost(cart_items, header_fields):
    rows = [calculate_purchase_row(it) for it in cart_items]
    total_net = sum((r["row_net_total"] for r in rows), Decimal('0'))
    total_net_safe = total_net if total_net != 0 else Decimal('1')

    total_addon = D(header_fields.get("header_freight_amount")) + D(header_fields.get("header_unload_amount")) + \
                  D(header_fields.get("header_labour_amount")) + D(header_fields.get("header_msc_charges")) + \
                  D(header_fields.get("header_gst_amount")) + D(header_fields.get("header_wht_amount")) + \
                  D(header_fields.get("header_advtax_amount")) + D(header_fields.get("header_delivery_charges"))

    total_header_disc = D(header_fields.get("header_discount_amount"))

    final_rows = []
    for r in rows:
        ratio = r["row_net_total"] / total_net_safe
        row_landed_total = r["row_net_total"] + (total_addon * ratio) - (total_header_disc * ratio)

        # COST PER BASE UNIT - THIS IS YOUR INVENTORY COST
        cost_denom = abs(r["eff_base_qty"])
        if cost_denom > 0:
            cost_per_base = abs(row_landed_total) / cost_denom
        else:
            cost_per_base = Decimal('0')

        # COST PER PACK - for display
        cost_per_pack = cost_per_base * r["pack_qty"]

        r["row_landed_total"] = row_landed_total.quantize(Decimal('0.01'), ROUND_HALF_UP)
        r["row_total_cost"] = cost_per_base.quantize(Decimal('0.0001'), ROUND_HALF_UP) # per base unit
        r["row_total_cost_per_pack"] = cost_per_pack.quantize(Decimal('0.01'), ROUND_HALF_UP)
        final_rows.append(r)

    return final_rows


