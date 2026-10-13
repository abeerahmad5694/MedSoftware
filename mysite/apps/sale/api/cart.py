from django.http import JsonResponse
from apps.sale.services.scan_barcode import scan_barcode,INVENTORY_FIELDS
from apps.inventory.models import Inventory








from django.http import JsonResponse


def speed_test(request):
    return JsonResponse({
        "success": True
    })










def _build_product_payload(product, weight_total=None):
    return {
        # ── Core Identity ────────────────────────────────────────────────
        'inv_id':    product.inv_id,
        'prod_name': product.prod_name,
        'barcode':   product.barcode  or '',
        'manualbc':  product.manualbc or '',
        'category':  product.category.name if product.category_id else '',

        # ── Scan Weight ──────────────────────────────────────────────────
        'weight_total': float(weight_total) if weight_total else 1,

        # ── Base / Retail  (modeId: 1) ───────────────────────────────────
        'base_price':    float(product.base_price    or product.rate or 0),
        'base_disc_per': float(product.base_disc_per or 0),
        'base_uom_name': product.base_uom.name    if product.base_uom_id    else '',  # ← .base_uom.name

        # ── Carton  (modeId: 2) ──────────────────────────────────────────
        'carton_price':    float(product.carton_price    or 0),
        'carton_disc_per': float(product.carton_disc_per or 0),
        'carton_uom_name': product.carton_uom.name if product.carton_uom_id else '',  # ← .carton_uom.name
        'carton_qty':      float(product.carton_qty      or 12),

        # ── Dozen  (modeId: 3) ───────────────────────────────────────────
        'dzn_price':    float(product.dzn_price    or 0),
        'dzn_disc_per': float(product.dzn_disc_per or 0),
        'dzn_uom_name': product.dzn_uom.name    if product.dzn_uom_id    else '',    # ← .dzn_uom.name
        'dzn_qty':      float(product.dzn_qty      or 12),

        # ── Wholesale  (modeId: 4) ───────────────────────────────────────
        'ws_price':    float(product.ws_price    or 0),
        'ws_disc_per': float(product.ws_disc_per or 0),
    }


import time

def add_cart(request):
    t_start = time.perf_counter()





    
    # if not request.user.is_authenticated:
    #     return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)

    code = (request.GET.get('code') or '').strip()
    barcode_scan = (request.GET.get('barcode_scan') or '').strip()
    
    t_input = time.perf_counter()
    print(f"[add_cart] Input parse took: {t_input - t_start:.6f} seconds")

    if not code:
        return JsonResponse({'success': False, 'message': 'No code provided'}, status=400)

    # ── Resolve product ──────────────────────────────────────────────────────
    t_scan_start = time.perf_counter()



    # product, weight_total = None , None
    product, weight_total = scan_barcode(request, code, barcode_scan)



    t_scan_end = time.perf_counter()
    print(f"[add_cart] scan_barcode service took: {t_scan_end - t_scan_start:.6f} seconds")

    if not product:
        return JsonResponse({'success': False, 'message': 'Inventory not found'}, status=404)

    t_build_start = time.perf_counter()
    payload = _build_product_payload(product, weight_total)
    t_build_end = time.perf_counter()
    
    
    print(f"[add_cart] _build_product_payload took: {t_build_end - t_build_start:.6f} seconds")
    t_json_start = time.perf_counter()
    
    
    
    response = JsonResponse({
        'success': True,
        'message': 'Item added to cart',
        'product': payload,
    })



    t_json_end = time.perf_counter()
    print(f"[add_cart] JsonResponse creation took: {t_json_end - t_json_start:.6f} seconds")
    print(f"[add_cart] Total view function execution took: {time.perf_counter() - t_start:.6f} seconds")
    
    
    return response