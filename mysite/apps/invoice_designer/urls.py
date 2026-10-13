from django.urls import path

from . import views

app_name = "invoice_designer"

urlpatterns = [
    path("designer/<str:document_type>/<str:page_type>/", views.DesignerView.as_view(), name="designer"),
    path("designer/", views.DesignerView.as_view(), name="designer_default"),

    path("api/configuration/", views.ConfigurationView.as_view(), name="api_configuration"),
    path("api/render/", views.RenderDocumentView.as_view(), name="api_render"),
    path("api/document-data/", views.DocumentDataView.as_view(), name="api_document_data"),
    path("api/field-registry/", views.FieldRegistryView.as_view(), name="api_field_registry"),
    path("api/page-types/<str:document_type>/", views.EnabledPageTypesView.as_view(), name="api_page_types"),
    path("api/upload-image/", views.UploadImageView.as_view(), name="api_upload_image"),
    path("api/company-preview/", views.CompanyPreviewView.as_view(), name="api_company_preview"),
]
