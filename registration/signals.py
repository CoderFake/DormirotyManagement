from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import RoomRegistration, Contract, CheckIn, CheckOut
from notification.models import Notification, NotificationCategory, UserNotification

@receiver(post_save, sender=RoomRegistration)
def create_registration_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi đăng ký phòng được tạo hoặc cập nhật trạng thái"""
    category, _ = NotificationCategory.objects.get_or_create(
        name="Đăng ký phòng",
        defaults={
            'icon': 'fa-home',
            'color': 'primary',
            'description': 'Thông báo về đăng ký phòng ở ký túc xá'
        }
    )
    
    if created:
        notification = Notification.objects.create(
            title="Đơn đăng ký phòng đã được tạo",
            content=f"Đơn đăng ký phòng của bạn đã được tạo thành công và đang chờ xét duyệt. Kỳ đăng ký: {instance.registration_period.name}.",
            category=category,
            sender_id=None, 
            priority="normal",
            is_global=False,
        )
        
        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )

        admin_category, _ = NotificationCategory.objects.get_or_create(
            name="Quản lý đăng ký",
            defaults={
                'icon': 'fa-clipboard-list',
                'color': 'info',
                'description': 'Thông báo cho quản trị viên về đăng ký phòng'
            }
        )
        
        from accounts.models import User
        admins = User.objects.filter(user_type__in=['admin', 'staff'], is_active=True)
        
        if admins.exists():
            admin_notification = Notification.objects.create(
                title="Có đơn đăng ký phòng mới",
                content=f"Sinh viên {instance.user.full_name} đã đăng ký phòng ở ký túc xá. Kỳ đăng ký: {instance.registration_period.name}.",
                category=admin_category,
                sender_id=None, 
                priority="normal",
                is_global=False,
            )
            
            for admin in admins:
                UserNotification.objects.create(
                    notification=admin_notification,
                    user=admin
                )
    
    elif not created and 'status' in kwargs.get('update_fields', []):
        if instance.status == 'approved':
            notification = Notification.objects.create(
                title="Đã tạo biên bản trả phòng",
                content=f"Biên bản trả phòng của bạn đã được tạo. Vui lòng kiểm tra thông tin và hoàn thành các thủ tục cần thiết.",
                category=category,
                sender_id=instance.checked_by_id,
                priority="normal",
                is_global=False,
            )
        
            UserNotification.objects.create(
                notification=notification,
                user=instance.contract.user
            )

        elif instance.status == 'rejected':
            notification = Notification.objects.create(
                title="Đơn đăng ký phòng bị từ chối",
                content=f"Đơn đăng ký phòng của bạn đã bị từ chối. Lý do: {instance.admin_notes or 'Không có lý do cụ thể.'}",
                category=category,
                sender_id=None, 
                priority="high",
                is_global=False,
            )
            
            UserNotification.objects.create(
                notification=notification,
                user=instance.user
            )
        

@receiver(post_save, sender=Contract)
def create_contract_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi hợp đồng được tạo hoặc cập nhật trạng thái"""
    
    category, _ = NotificationCategory.objects.get_or_create(
        name="Hợp đồng",
        defaults={
            'icon': 'fa-file-contract',
            'color': 'success',
            'description': 'Thông báo về hợp đồng thuê phòng'
        }
    )
    
    if created:
        notification = Notification.objects.create(
            title="Hợp đồng mới đã được tạo",
            content=f"Hợp đồng thuê phòng của bạn đã được tạo. Số hợp đồng: {instance.contract_number}. Vui lòng kiểm tra và xác nhận hợp đồng.",
            category=category,
            sender_id=None,  # Hệ thống tự động
            priority="normal",
            is_global=False,
        )
        
        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )
    
    elif not created:
        if instance.signed_by_student and not instance.signed_by_admin:
            admin_category, _ = NotificationCategory.objects.get_or_create(
                name="Quản lý hợp đồng",
                defaults={
                    'icon': 'fa-file-signature',
                    'color': 'info',
                    'description': 'Thông báo cho quản trị viên về hợp đồng'
                }
            )
            
            from accounts.models import User
            admins = User.objects.filter(user_type__in=['admin', 'staff'], is_active=True)
            
            if admins.exists():
                admin_notification = Notification.objects.create(
                    title="Sinh viên đã ký hợp đồng",
                    content=f"Sinh viên {instance.user.full_name} đã ký hợp đồng #{instance.contract_number}. Vui lòng xem xét và ký duyệt hợp đồng.",
                    category=admin_category,
                    sender_id=None,
                    priority="normal",
                    is_global=False,
                )
                
                for admin in admins:
                    UserNotification.objects.create(
                        notification=admin_notification,
                        user=admin
                    )
        
        elif instance.signed_by_student and instance.signed_by_admin:
            notification = Notification.objects.create(
                title="Hợp đồng đã được ký đầy đủ",
                content=f"Hợp đồng #{instance.contract_number} đã được ký duyệt đầy đủ và có hiệu lực từ ngày {instance.start_date.strftime('%d/%m/%Y')} đến ngày {instance.end_date.strftime('%d/%m/%Y')}.",
                category=category,
                sender_id=None,
                priority="high",
                is_global=False,
            )
            
            UserNotification.objects.create(
                notification=notification,
                user=instance.user
            )

@receiver(post_save, sender=CheckIn)
def create_checkin_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi sinh viên nhận phòng"""
    
    if created or (not created and instance.is_completed):
        category, _ = NotificationCategory.objects.get_or_create(
            name="Nhận phòng",
            defaults={
                'icon': 'fa-key',
                'color': 'info',
                'description': 'Thông báo về nhận phòng ký túc xá'
            }
        )
        
        if instance.is_completed:
            notification = Notification.objects.create(
                title="Hoàn thành nhận phòng",
                content=f"Bạn đã hoàn thành thủ tục nhận phòng. Phòng: {instance.contract.room.building.name} - {instance.contract.room.room_number}, Giường: {instance.contract.bed.bed_number}.",
                category=category,
                sender_id=instance.checked_by_id,
                priority="normal",
                is_global=False,
            )
        else:
            notification = Notification.objects.create(
                title="Đã tạo biên bản nhận phòng",
                content=f"Biên bản nhận phòng của bạn đã được tạo. Vui lòng kiểm tra thông tin và hoàn thành các thủ tục cần thiết.",
                category=category,
                sender_id=instance.checked_by_id,
                priority="normal",
                is_global=False,
            )
        
        UserNotification.objects.create(
            notification=notification,
            user=instance.contract.user
        )


@receiver(post_save, sender=CheckOut)
def create_checkout_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi sinh viên trả phòng"""

    category, _ = NotificationCategory.objects.get_or_create(
        name="Trả phòng",
        defaults={
            'icon': 'fa-door-open',
            'color': 'warning',
            'description': 'Thông báo về việc trả phòng ký túc xá'
        }
    )

    if created:
        notification = Notification.objects.create(
            title="Biên bản trả phòng đã được tạo",
            content=f"Biên bản trả phòng của bạn đã được tạo. Vui lòng kiểm tra thông tin và hoàn thành các thủ tục cần thiết.",
            category=category,
            sender_id=instance.checked_by_id,
            priority="normal",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.contract.user
        )

        admin_category, _ = NotificationCategory.objects.get_or_create(
            name="Quản lý trả phòng",
            defaults={
                'icon': 'fa-clipboard-check',
                'color': 'warning',
                'description': 'Thông báo cho quản trị viên về trả phòng'
            }
        )

        from accounts.models import User
        admins = User.objects.filter(user_type__in=['admin', 'staff'], is_active=True)

        if admins.exists():
            admin_notification = Notification.objects.create(
                title="Có biên bản trả phòng mới",
                content=f"Sinh viên {instance.contract.user.full_name} đã tạo biên bản trả phòng {instance.contract.room.building.name} - {instance.contract.room.room_number}.",
                category=admin_category,
                sender_id=None,
                priority="normal",
                is_global=False,
            )

            for admin in admins:
                UserNotification.objects.create(
                    notification=admin_notification,
                    user=admin
                )

    elif not created and instance.is_completed:
        notification = Notification.objects.create(
            title="Đã hoàn thành trả phòng",
            content=f"Bạn đã hoàn thành thủ tục trả phòng {instance.contract.room.building.name} - {instance.contract.room.room_number}. Cảm ơn bạn đã sử dụng dịch vụ của chúng tôi!",
            category=category,
            sender_id=instance.checked_by_id,
            priority="high",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.contract.user
        )