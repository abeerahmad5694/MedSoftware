from django.urls import path

from apps.diary import views

app_name = "diary"

urlpatterns = [
    path("", views.diary_home, name="home"),
    path("api/items/", views.api_create, name="api_create"),
    path("api/items/<int:item_id>/", views.api_item, name="api_item"),
    path("api/items/<int:item_id>/update/", views.api_update, name="api_update"),
    path("api/items/<int:item_id>/action/", views.api_action, name="api_action"),
    path("api/items/<int:item_id>/delete/", views.api_delete, name="api_delete"),
    path("api/items/<int:item_id>/history/", views.api_history, name="api_history"),
]
