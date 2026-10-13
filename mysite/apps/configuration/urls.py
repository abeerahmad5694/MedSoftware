from django.urls import path
from apps.configuration.views import company, branch, posterminal, company_config, defaultaccounts

urlpatterns = [
    path('', company.company, name='company'),
    path('branch/', branch.branch, name='branch'),
    path('posterminal/', posterminal.posterminal, name='posterminal'),
    path('config/', company_config.company_config_view, name='company_config'),
    path('default-accounts/', defaultaccounts.default_accounts_view, name='default_accounts'),
    path('api/get-config/', company_config.get_company_config_api, name='get_company_config_api'),
]

