import json
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import connection, transaction
from django.apps import apps

from apps.inventory.models import Inventory, StockLot, StockLedger
from apps.sale.models import Invoice
from apps.quotation.models import Quotation
from apps.purchase.models import Purchase, PurchaseOrder
from apps.myledger.models import Gledg, Vchno

# Try importing historical models if present
try:
    from apps.sale.models import HistoricalInvoice
except ImportError:
    HistoricalInvoice = None

try:
    from apps.quotation.models import HistoricalQuotation
except ImportError:
    HistoricalQuotation = None


def _truncate_model(model):
    """
    Truncates a model's table and resets primary key auto-increment.
    Works seamlessly across SQLite, MySQL, and PostgreSQL.
    """
    if not model:
        return 0
    table_name = model._meta.db_table
    count = model.objects.count()
    with connection.cursor() as cursor:
        engine = connection.settings_dict.get('ENGINE', '')
        if 'sqlite3' in engine:
            try:
                cursor.execute("PRAGMA foreign_keys = OFF;")
                cursor.execute(f"DELETE FROM `{table_name}`;")
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}';")
            finally:
                cursor.execute("PRAGMA foreign_keys = ON;")
        elif 'mysql' in engine:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute(f"TRUNCATE TABLE `{table_name}`;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        elif 'postgresql' in engine:
            cursor.execute(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE;')
        else:
            model.objects.all().delete()
    return count


@login_required
def clear_data_page(request):
    """
    Renders the System Data Management & Purge screen.
    """
    engine = connection.settings_dict.get('ENGINE', '').split('.')[-1].upper()
    context = {
        'db_engine': engine,
        'user_name': request.user.get_full_name() or request.user.username,
        'is_staff': request.user.is_staff or request.user.is_superuser,
    }
    return render(request, 'myglobal/clear_data.html', context)


@login_required
def get_data_counts(request):
    """
    Returns live database counts for all purgable tables.
    """
    try:
        counts = {
            'inventory': Inventory.objects.count(),
            'stock_lot': StockLot.objects.count(),
            'stock_ledger': StockLedger.objects.count(),
            'sale': Invoice.objects.count(),
            'quotation': Quotation.objects.count(),
            'purchase': Purchase.objects.count(),
            'purchase_order': PurchaseOrder.objects.count(),
            'gledg': Gledg.objects.count(),
        }

        vouchers = []
        for v in Vchno.objects.all().order_by('TYPE'):
            vouchers.append({
                'type': v.TYPE,
                'vchno': v.VCHNO,
                'remarks': v.REMARKS or '',
            })

        return JsonResponse({
            'success': True,
            'counts': counts,
            'vouchers': vouchers,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@transaction.atomic
def execute_clear_data(request):
    """
    Executes table truncation and voucher resets based on user selection.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST method required.'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        clear_inventory = payload.get('clear_inventory', False)
        clear_sale = payload.get('clear_sale', False)
        clear_quotation = payload.get('clear_quotation', False)
        clear_purchase = payload.get('clear_purchase', False)
        clear_stock = payload.get('clear_stock', False)
        clear_ledger = payload.get('clear_ledger', False)
        reset_vouchers = payload.get('reset_vouchers', False)
        voucher_types = payload.get('voucher_types', [])

        deleted_summary = {}

        # 1. Clear Purchase (also auto-clears Stock Lot and Stock Ledger as requested)
        if clear_purchase:
            deleted_summary['Purchases'] = _truncate_model(Purchase)
            deleted_summary['Purchase Orders'] = _truncate_model(PurchaseOrder)
            # Auto delete stock lot and stock ledger
            deleted_summary['Stock Lots'] = _truncate_model(StockLot)
            deleted_summary['Stock Ledger'] = _truncate_model(StockLedger)

        # 2. Clear Stock Ledger & Stock Lot explicitly if requested
        elif clear_stock:
            deleted_summary['Stock Lots'] = _truncate_model(StockLot)
            deleted_summary['Stock Ledger'] = _truncate_model(StockLedger)

        # 3. Clear Inventory Items
        if clear_inventory:
            deleted_summary['Inventory Items'] = _truncate_model(Inventory)
            # If stock lots/ledger weren't already wiped, wipe them to avoid orphan references
            if 'Stock Lots' not in deleted_summary:
                deleted_summary['Stock Lots'] = _truncate_model(StockLot)
            if 'Stock Ledger' not in deleted_summary:
                deleted_summary['Stock Ledger'] = _truncate_model(StockLedger)

        # 4. Clear Sales / Invoices
        if clear_sale:
            deleted_summary['Invoices'] = _truncate_model(Invoice)
            if HistoricalInvoice:
                deleted_summary['Historical Invoices'] = _truncate_model(HistoricalInvoice)

        # 5. Clear Quotations
        if clear_quotation:
            deleted_summary['Quotations'] = _truncate_model(Quotation)
            if HistoricalQuotation:
                deleted_summary['Historical Quotations'] = _truncate_model(HistoricalQuotation)

        # 6. Clear General Ledger (Gledg)
        if clear_ledger:
            deleted_summary['Ledger (Gledg)'] = _truncate_model(Gledg)

        # 7. Reset Voucher Sequences (Vchno)
        vouchers_reset_count = 0
        if reset_vouchers:
            qs = Vchno.objects.all()
            if voucher_types and 'ALL' not in voucher_types:
                qs = qs.filter(TYPE__in=voucher_types)
            vouchers_reset_count = qs.update(VCHNO=0)
            deleted_summary['Voucher Sequences Reset'] = vouchers_reset_count

        return JsonResponse({
            'success': True,
            'message': 'Requested database operations completed successfully.',
            'summary': deleted_summary,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

