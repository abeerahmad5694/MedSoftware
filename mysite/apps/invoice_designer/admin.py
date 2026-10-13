from django.contrib import admin

from .models import TemplateConfiguration


@admin.register(TemplateConfiguration)
class TemplateConfigurationAdmin(admin.ModelAdmin):
    list_display = ("document_type", "page_type", "name", "is_enabled", "is_default", "updated_at")
    list_filter = ("document_type", "page_type", "is_enabled", "is_default")
    search_fields = ("name",)
    readonly_fields = ("created_at", "updated_at")
