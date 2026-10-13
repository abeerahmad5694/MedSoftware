# sale/urls.py
from django.urls import path
from . import views
from apps.sale.api.invoice_crud import save_bill ,get_bill ,delete_sale_bill
from apps.sale.api.cart import add_cart , speed_test
app_name = "sale"

urlpatterns = [
    path('', views.sale_page, name='main_sale'),

    path('speed-test/', speed_test, name='speed_test'),
    path("Pos_features/", views.get_features, name="Pos_features"),

   
]
# apis 
urlpatterns +=[
    path('api/add_cart/', add_cart, name='add_cart'),
    path("api/save_bills/", save_bill, name="save_bill"), 
    path('api/get_bill/<int:bill_no>/',get_bill,name="get_bill"),

    path("api/delete_sale_bill/<str:pur_inv>/<int:bill_no>/",delete_sale_bill,name="delete_sale_bill"), 
]