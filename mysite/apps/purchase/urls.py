from django.urls import path
from . import views
from .api.purchase_crud import save_bill,get_bill

urlpatterns =[
    path('',views.purchase , name = 'main_purchase')
]



# apis 
urlpatterns +=[
    # path('api/add_cart/', add_cart, name='add_cart'),
    path("api/save_bills/", save_bill, name="save_bill"), 
    path('api/get_bill/<int:bill_no>/',get_bill,name="get_bill"),
]