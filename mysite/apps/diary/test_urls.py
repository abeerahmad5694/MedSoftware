from django.http import HttpResponse
from django.urls import include, path


def _test_stub(request, *args, **kwargs):
    return HttpResponse("")


urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("diary/", include("apps.diary.urls")),
]

# The ERP shell has legacy URL tags inside HTML comments. These names are only
# needed to render that shared shell in focused Diary tests.
for _name in (
    "main_purchase",
    "item_wise_profit_and_loss",
    "bill_wise_profit_and_loss",
    "quotation_book",
    "comprehensive_sale",
    "accounts_receivable",
    "accounts_payable",
):
    urlpatterns.append(path(f"test-stubs/{_name}/", _test_stub, name=_name))
