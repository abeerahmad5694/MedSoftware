from django.apps import AppConfig


class MyledgerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.myledger'
    # def ready(self):
    #     import myledger.signals
        