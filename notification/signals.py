from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification, UserNotification

@receiver(post_save, sender=Notification)
def distribute_notifications(sender, instance, created, **kwargs):
    """Phân phối thông báo đến người dùng khi thông báo mới được tạo"""
    
    if created and instance.is_global:
        from accounts.models import User
        users = User.objects.filter(is_active=True)

        for user in users:
            UserNotification.objects.create(
                notification=instance,
                user=user
            )
    