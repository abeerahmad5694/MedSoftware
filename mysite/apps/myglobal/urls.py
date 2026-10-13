from django.urls import path
from .views import global_inline_modal , local_storage_utills , page_not_found

# app_name = 'global'/

urlpatterns = [
    path('page_not_found/', page_not_found.page_not_found, name='page_not_found'),
    path('lookup/<str:app_label>/<str:model_name>/', global_inline_modal.generic_lookup_create, name='generic_lookup_create'),
    path('fetch_full_model/<str:app_label>/<str:model_name>/', local_storage_utills.fetch_full_model, name='fetch_full_model'),
    path('sync_indexdb/<str:app_label>/<str:model_name>/', local_storage_utills.sync_indexdb , name='sync_indexdb'),
]
