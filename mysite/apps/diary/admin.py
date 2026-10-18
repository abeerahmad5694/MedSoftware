from django.contrib import admin

from apps.diary.models import DiaryHistory, DiaryItem


class DiaryHistoryInline(admin.TabularInline):
    model = DiaryHistory
    fk_name = "dairyitem"
    extra = 0
    can_delete = False
    readonly_fields = (
        "action",
        "amount",
        "reason",
        "note",
        "old_due_date",
        "new_due_date",
        "old_amount",
        "new_amount",
        "balance_after",
        "created_at",
    )


@admin.register(DiaryItem)
class DiaryItemAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "title", "acc_code", "scheduled_date", "remaining_amount", "status", "branch")
    list_filter = ("kind", "status", "scheduled_date", "company", "branch")
    search_fields = ("title", "details", "=acc_code")
    readonly_fields = ("original_due_date", "created_at", "updated_at", "deleted_at")
    inlines = (DiaryHistoryInline,)


@admin.register(DiaryHistory)
class DiaryHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "dairyitem", "action", "amount", "reason", "created_at")
    list_filter = ("action", "reason", "created_at")
    search_fields = ("dairyitem__title", "=dairyitem__acc_code", "note")
    readonly_fields = [field.name for field in DiaryHistory._meta.fields]
