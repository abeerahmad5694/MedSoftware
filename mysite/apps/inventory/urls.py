from django.urls import path
from .views.inventory import inventory, get_item_by_id
from apps.inventory.api import inventory as api
from .views.stock_audit import stock_audit, stock_audit_items, save_stock_audit
from .views import stock_adjustment
from apps.inventory.views.item_ledger import item_ledger


urlpatterns = [
    path('', inventory, name='inventory'),
    path('get_item_by_id/<int:inv_id>/', get_item_by_id, name='get_item_by_id'),
]

urlpatterns += [
    path('api/save_update_inventory', api.save_update_inventory, name='save_update_inventory'),
    path('api/delete_inventory_item/<int:inv_id>/', api.delete_inventory, name='delete_inventory'),


    path('stock-audit/', stock_audit, name='stock_audit'),
    path('api/stock-audit/items/', stock_audit_items, name='stock_audit_items'),
    path('api/stock-audit/save/', save_stock_audit, name='save_stock_audit'),
    
    path('stock-adjustment/', stock_adjustment.stock_adjustment_page, name='stock_adjustment'),
    path('api/stock-adjustment/items/', stock_adjustment.get_inventory_list, name='get_inventory_list_adj'),
    path('api/stock-adjustment/save/', stock_adjustment.save_stock_adjustment, name='save_stock_adjustment'),
    
    path('item-ledger/', item_ledger, name='item_ledger'),
]