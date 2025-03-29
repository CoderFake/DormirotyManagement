from django.apps import AppConfig


class MaintenanceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'maintenance'
    verbose_name = 'Quản lý Bảo trì'

    def ready(self):
        import maintenance.signals