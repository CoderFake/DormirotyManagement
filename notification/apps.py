from django.apps import AppConfig


class NotificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notification'
    verbose_name = 'Quản lý Thông báo'

    def ready(self):
        import notification.signals