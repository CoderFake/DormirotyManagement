from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import User, UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Tạo hồ sơ người dùng khi tạo tài khoản mới"""
    if created:
        if instance._state.adding is False:
            try:
                if not UserProfile.objects.filter(user=instance).exists():
                    UserProfile.objects.create(user=instance)
            except Exception as e:
                print(f"Lỗi tạo UserProfile: {e}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Cập nhật hồ sơ người dùng khi cập nhật tài khoản"""
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except Exception as e:
        print(f"Lỗi lưu UserProfile: {e}")