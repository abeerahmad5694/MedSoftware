from django.apps import AppConfig


class MyaccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.myaccounts'


    def ready(self):
        import apps.myaccounts.signals  
