# sale/urls.py
from django.urls import path
from . import views
from apps.quotation.api.quotation_crud import save_bill ,get_bill
from apps.quotation.api.cart import add_cart
# app_name = "sale"

urlpatterns = [
    path('', views.sale_page, name='main_quotation'),
    

    
    # path("get_bill/", views.get_bill, name="get_bill"),
    # path("qz-sign", views.qz_sign, name="qz_sign"),
    path("Pos_features/", views.get_features, name="Pos_features"),

   
]
# apis 
urlpatterns +=[
    path('api/add_cart/', add_cart, name='add_cart'),
    path("api/save_bills/", save_bill, name="save_bill"), 
    path('api/get_bill/<int:bill_no>/',get_bill,name="get_bill"),
]