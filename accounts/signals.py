from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Tạo hồ sơ người dùng khi tạo tài khoản mới"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Cập nhật hồ sơ người dùng khi cập nhật tài khoản"""
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()