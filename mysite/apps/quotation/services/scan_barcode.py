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
     'category',
    # Base
    'base_price', 'base_disc_per', 'base_uom',       # ← FK id field only
    # Carton
    'carton_price', 'carton_disc_per', 'carton_uom', 'carton_qty',
    'dzn_price', 'dzn_disc_per', 'dzn_uom', 'dzn_qty',
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

def scan_barcode(request, code: str,barcode_scan=False):
    """
    O(1) barcode resolver:
    - Step 1: Single Q() query covering manualbc + barcode + inv_id
    - Step 2: Weighted barcode parse + single Q() query if length matches config
    Returns: (product | None, weight_total | None)
    """
    config = _get_barcode_config()
    weight_total = None
    product = None

    # ── Step 1: Single combined query (O(1) with DB indexes) ───────────────
    if barcode_scan:
        direct_q = Q(manualbc__iexact=code) | Q(barcode=code)
    else:
        direct_q = Q(manualbc__iexact=code)

    if code.isdigit():
        direct_q |= Q(inv_id=int(code))

    product = _fetch_product(direct_q)
    if product:
        return product, None

    # ── Step 2: Weighted barcode (only if length matches config) ────────────
    if len(code) != config.total_bc_digits and not barcode_scan:
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
        return None, None

    # Single query for weighted item_code
    weighted_q = Q(barcode=item_code) | Q(manualbc__iexact=item_code) | Q(barcode2__endswith=item_code)
    if item_code.isdigit():
        weighted_q |= Q(inv_id=int(item_code))

    product = _fetch_product(weighted_q)
    return product, weight_total