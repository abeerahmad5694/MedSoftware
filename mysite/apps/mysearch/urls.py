from django.urls import path
from . import views

urlpatterns = [
    path('search/<str:app_label>/<str:model_name>/', views.global_search, name='global_search'),
]
