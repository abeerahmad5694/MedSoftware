from django.urls import path
from .views import users , permissions , validate_license

# app_name = 'users'

urlpatterns = [
    path('', users.users, name='users'),
    path('permissions/', permissions.permissions, name='permissions'),
    path('api/validate_license/', validate_license.validate_license_api, name='validate_license'),

]
