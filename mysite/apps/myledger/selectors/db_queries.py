from apps.myaccounts.models import Accounts
from apps.myledger.models import Gledg
from django.core.cache import cache


def get_all_bank_accounts():
    cache_key = 'bank_accounts_list'
    result = cache.get(cache_key)
    if result is None:
        result = list(
            Accounts.objects.filter(ACC_CODE__startswith='11100000')
            .order_by('ACC_CODE')
            .values('ACC_CODE', 'ACC_NAME')
        )
        cache.set(cache_key, result, timeout=300)  # 5 min cache
    return result
