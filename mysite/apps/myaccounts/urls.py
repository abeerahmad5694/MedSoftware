from django.urls import path
from apps.myaccounts.views import quick_accounts, chart_of_accounts
from apps.myaccounts.api.global_accounts_form_modal import save_update_account , get_account,get_next_account_code
from apps.myaccounts.api.chart_of_accounts_api import get_group_tree, get_detail_accounts

urlpatterns = [
    path('', quick_accounts.quick_accounts, name='quick_accounts'),
    path('chart-of-accounts/', chart_of_accounts.chart_of_accounts, name='chart_of_accounts'),
    path('api/save/<int:acc_code>/',save_update_account, name='save_update_account'),
    path('api/get/<int:acc_code>/',get_account, name='get_account'),
    path('api/get-next-account-code/',get_next_account_code, name='get_next_account_code'),
    path('api/get-group-tree/', get_group_tree, name='get_group_tree'),
    path('api/get-detail-accounts/', get_detail_accounts, name='get_detail_accounts'),

    
]
