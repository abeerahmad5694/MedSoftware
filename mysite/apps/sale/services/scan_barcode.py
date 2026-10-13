import time
from decimal import Decimal, InvalidOperation
from django.db.models import Q
from apps.inventory.models import Inventory
from apps.sale.models import BarcodConfig

# ── Module-level config cache (avoid DB hit on every scan) ──────────────────
_barcode_config_cache = None

def _get_barcode_config():
    global _barcode_config_cache
    if _barcode_config_cache is None:
        _barcode_config_cache, _ = BarcodConfig.objects.get_or_create(
            user='main_bc',
            defaults={'price_base': 'N'}
        )
    return _barcode_config_cache

# ── Correct field selector for .only() with FK relations ───────────────────
INVENTORY_FIELDS = (
    'inv_id', 'prod_name', 'barcode', 'manualbc',
    'category_id', 'category__name',
    # Base
    'base_price', 'base_disc_per', 'base_uom_id', 'base_uom__name',
    # Carton
    'carton_price', 'carton_disc_per', 'carton_uom_id', 'carton_uom__name', 'carton_qty',
    'dzn_price', 'dzn_disc_per', 'dzn_uom_id', 'dzn_uom__name', 'dzn_qty',
    'ws_price', 'ws_disc_per',
)

def _fetch_product(filter_q):
    return (
        Inventory.objects
        .filter(filter_q)
        .select_related('category', 'base_uom', 'carton_uom', 'dzn_uom')  # ← JOIN uom tables
        .only(*INVENTORY_FIELDS)
        .first()
    )

def scan_barcode(request, code: str, barcode_scan=False):
   
    start_total = time.perf_counter()
    config = _get_barcode_config()
    weight_total = None
    product = None

    # Normalise inputs to avoid case mismatch while keeping lookups index-friendly
    code_variants = list(set([code, code.lower(), code.upper()]))

    # ── Step 1: Single combined query (O(1) with DB indexes) ───────────────
    if barcode_scan:
        direct_q = Q(manualbc__in=code_variants) | Q(barcode__in=code_variants)
    else:
        direct_q = Q(manualbc__in=code_variants)

    if code.isdigit():
        direct_q |= Q(inv_id=int(code))

    t0 = time.perf_counter()
    product = _fetch_product(direct_q)
    t1 = time.perf_counter()
    print(f"[scan_barcode] Step 1 Query (Exact match) took: {t1 - t0:.6f} seconds")

    if product:
        print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
        return product, None

    # ── Step 2: Weighted barcode (only if length matches config) ────────────
    if len(code) != config.total_bc_digits and not barcode_scan:
        print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
        return None, None

    try:
        trimmed   = code[config.left_delete : len(code) - config.right_delete]
        item_code = trimmed[:config.item_bc]
        w_part    = trimmed[config.item_bc:]
        kg        = w_part[:config.kg]
        gr        = w_part[config.kg : config.kg + config.grm]
        weight_total = Decimal(f"{kg}.{gr}")
        print('weight total is ',weight_total,kg,gr)
    except (InvalidOperation, ValueError, IndexError) as e:
        print(f"[scan_barcode] Weighted parse error: {e}")
        print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
        return None, None

    # Single query for weighted item_code using fast IN check
    item_code_variants = list(set([item_code, item_code.lower(), item_code.upper()]))
    weighted_q = Q(barcode__in=item_code_variants) | Q(manualbc__in=item_code_variants)
    if item_code.isdigit():
        weighted_q |= Q(inv_id=int(item_code))

    t0 = time.perf_counter()
    product = _fetch_product(weighted_q)
    t1 = time.perf_counter()
    print(f"[scan_barcode] Step 2 Query (Weighted code) took: {t1 - t0:.6f} seconds")

    if product:
        print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
        return product, weight_total

    # ── Step 3: Defer slow trailing wildcards as final fallback ────────────
    if len(item_code) > 0:
        fallback_q = Q(barcode2__endswith=item_code)
        t0 = time.perf_counter()
        product = _fetch_product(fallback_q)
        t1 = time.perf_counter()
        print(f"[scan_barcode] Step 3 Query (Endswith wildcard) took: {t1 - t0:.6f} seconds")
        if product:
            print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
            return product, weight_total

    print(f"[scan_barcode] Total execution time: {time.perf_counter() - start_total:.6f} seconds")
    return None, None
