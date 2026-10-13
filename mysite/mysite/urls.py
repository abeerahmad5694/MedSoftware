"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from apps.myglobal.views.debug_view import debug_auth

urlpatterns = [
    path('admin/', admin.site.urls),
    path('debug/', debug_auth),           # TEMP: remove after diagnosis
    path('', include('django.contrib.auth.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('myaccounts/', include('apps.myaccounts.urls')),
    path('sale/', include('apps.sale.urls')),
    path('quotation/', include('apps.quotation.urls')),
    path('invoice-designer/', include('apps.invoice_designer.urls')),
    path('purchase/', include('apps.purchase.urls')),
    path('configuration/', include('apps.configuration.urls')),
    path('myglobal/', include('apps.myglobal.urls')),
    path('users/', include('apps.users.urls')),
    path('mysearch/', include('apps.mysearch.urls')),
    path('myledger/', include('apps.myledger.urls')),
    path('reports/', include('apps.reports.urls')),
    path('dashboard/', include('apps.dashbaord.urls')),
]
# Serve media files (user uploads: logos, images) using Django's serve view directly.
# This bypasses the DEBUG check in static() and works with waitress/gunicorn/any WSGI server.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)