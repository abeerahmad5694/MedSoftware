from django.urls import path
from apps.myledger.views import general_ledger
from apps.myledger.views.vouchers import jv_voucher_page, dynamic_voucher_page

urlpatterns = [
    path('general_ledger/', general_ledger.general_ledger, name='general_ledger'),
    
    path('jv_voucher_page/', jv_voucher_page, name='jv_voucher_page'),
    path('jv_voucher_page/<str:v_type>/', jv_voucher_page, name='jv_voucher_page_vtype'),
    path('jv_voucher_page/<str:v_type>/<int:vno>/', jv_voucher_page, name='jv_voucher_page_edit'),
    
    path('dynamic_voucher_page/', dynamic_voucher_page, name='dynamic_voucher_page'),
    path('dynamic_voucher_page/<str:v_type>/', dynamic_voucher_page, name='dynamic_voucher_page_vtype'),
    path('dynamic_voucher_page/<str:v_type>/<int:vno>/', dynamic_voucher_page, name='dynamic_voucher_page_edit'),
]
# voucher apis
from apps.myledger.api.vouchers import get_all_banks
from apps.myledger.api.vouchers import save_dynamic_voucher
from apps.myledger.api.vouchers import delete_dynamic_voucher , get_dynamic_voucher
urlpatterns += [
    path('api/get_banks/',get_all_banks, name='get_banks'),
    path('api/save_dynamic_voucher/',save_dynamic_voucher, name='save_dynamic_voucher'),
    path('api/delete_dynamic_voucher/',delete_dynamic_voucher, name='delete_dynamic_voucher'),
    path('api/get_voucher_for_edit/<int:vno>/<str:v_type>/', get_dynamic_voucher, name='get_voucher_for_edit'),
]

# general ledger apis
from apps.myledger.api.general_ledger import general_ledger
urlpatterns += [
    path('api/general_ledger/<int:acc_code>/<str:from_date>/<str:to_date>/',general_ledger, name='general_ledger_api'),
]