from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import MaintenanceRequest, MaintenanceComment
from notification.models import Notification, NotificationCategory, UserNotification

@receiver(post_save, sender=MaintenanceRequest)
def create_maintenance_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi yêu cầu bảo trì được tạo hoặc cập nhật trạng thái"""

    category, _ = NotificationCategory.objects.get_or_create(
        name="Bảo trì",
        defaults={
            'icon': 'fa-tools',
            'color': 'info',
            'description': 'Thông báo về yêu cầu bảo trì'
        }
    )
    
    if created:
        notification = Notification.objects.create(
            title="Yêu cầu bảo trì đã được tạo",
            content=f"Yêu cầu bảo trì '{instance.title}' của bạn đã được ghi nhận và đang chờ xử lý. Mã yêu cầu: {instance.request_number}.",
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
            name="Quản lý bảo trì",
            defaults={
                'icon': 'fa-wrench',
                'color': 'warning',
                'description': 'Thông báo cho quản trị viên về yêu cầu bảo trì'
            }
        )
        
        from accounts.models import User
        admins = User.objects.filter(user_type__in=['admin', 'staff'], is_active=True)
        
        if admins.exists():
            priority = 'normal'
            if instance.priority in ['high', 'urgent']:
                priority = instance.priority
                
            admin_notification = Notification.objects.create(
                title=f"Có yêu cầu bảo trì mới ({instance.get_priority_display()})",
                content=f"Sinh viên {instance.user.full_name} đã tạo yêu cầu bảo trì '{instance.title}'. Phòng: {instance.room.building.name} - {instance.room.room_number}.",
                category=admin_category,
                sender_id=None,
                priority=priority,
                is_global=False,
            )
            
            for admin in admins:
                UserNotification.objects.create(
                    notification=admin_notification,
                    user=admin
                )
    
    else: 
        old_status = instance.status
        if 'status' in kwargs.get('update_fields', []) or old_status != instance.status:
            if instance.status == 'assigned':
                notification = Notification.objects.create(
                    title="Yêu cầu bảo trì đã được phân công",
                    content=f"Yêu cầu bảo trì '{instance.title}' (Mã: {instance.request_number}) đã được phân công cho nhân viên kỹ thuật và sẽ được xử lý trong thời gian sớm nhất.",
                    category=category,
                    sender_id=None,
                    priority="normal",
                    is_global=False,
                )
                
                UserNotification.objects.create(
                    notification=notification,
                    user=instance.user
                )
                
                if instance.assigned_to:
                    staff_notification = Notification.objects.create(
                        title="Bạn được phân công xử lý yêu cầu bảo trì",
                        content=f"Bạn đã được phân công xử lý yêu cầu bảo trì '{instance.title}' tại phòng {instance.room.building.name} - {instance.room.room_number}.",
                        category=category,
                        sender_id=None,
                        priority=instance.priority,
                        is_global=False,
                    )
                    
                    UserNotification.objects.create(
                        notification=staff_notification,
                        user=instance.assigned_to
                    )
            
            elif instance.status == 'in_progress':
                notification = Notification.objects.create(
                    title="Yêu cầu bảo trì đang được xử lý",
                    content=f"Yêu cầu bảo trì '{instance.title}' (Mã: {instance.request_number}) đang được xử lý bởi nhân viên kỹ thuật.",
                    category=category,
                    sender_id=None,
                    priority="normal",
                    is_global=False,
                )
                
                UserNotification.objects.create(
                    notification=notification,
                    user=instance.user
                )
            
            elif instance.status == 'completed':
                notification = Notification.objects.create(
                    title="Yêu cầu bảo trì đã hoàn thành",
                    content=f"Yêu cầu bảo trì '{instance.title}' (Mã: {instance.request_number}) đã được hoàn thành. Vui lòng kiểm tra và phản hồi nếu cần thiết.",
                    category=category,
                    sender_id=None,
                    priority="normal",
                    is_global=False,
                )
                
                UserNotification.objects.create(
                    notification=notification,
                    user=instance.user
                )
            
            elif instance.status == 'rejected':
                notification = Notification.objects.create(
                    title="Yêu cầu bảo trì bị từ chối",
                    content=f"Yêu cầu bảo trì '{instance.title}' (Mã: {instance.request_number}) đã bị từ chối. Lý do: {instance.admin_notes or 'Không có lý do cụ thể.'}",
                    category=category,
                    sender_id=None,
                    priority="normal",
                    is_global=False,
                )
                
                UserNotification.objects.create(
                    notification=notification,
                    user=instance.user
                )

@receiver(post_save, sender=MaintenanceComment)
def create_maintenance_comment_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi có bình luận mới trên yêu cầu bảo trì"""
    
    if created:
        maintenance_request = instance.maintenance_request
        
        category, _ = NotificationCategory.objects.get_or_create(
            name="Bình luận bảo trì",
            defaults={
                'icon': 'fa-comment',
                'color': 'secondary',
                'description': 'Thông báo về bình luận yêu cầu bảo trì'
            }
        )
        
        recipients = []
        
        if instance.user == maintenance_request.user:
            if maintenance_request.assigned_to:
                recipients.append(maintenance_request.assigned_to)

            from accounts.models import User
            related_comments = MaintenanceComment.objects.filter(
                maintenance_request=maintenance_request
            ).exclude(user=instance.user)
            
            staff_who_commented = User.objects.filter(
                user_type__in=['admin', 'staff'],
                id__in=related_comments.values_list('user_id', flat=True)
            )
            
            recipients.extend(staff_who_commented)
        
        else:
            recipients.append(maintenance_request.user)
        notification = Notification.objects.create(
            title=f"Bình luận mới trên yêu cầu bảo trì #{maintenance_request.request_number}",
            content=f"{instance.user.full_name} đã bình luận về yêu cầu bảo trì '{maintenance_request.title}': {instance.comment[:100]}{'...' if len(instance.comment) > 100 else ''}",
            category=category,
            sender_id=instance.user.id,
            priority="normal",
            is_global=False,
        )

        for recipient in recipients:
            UserNotification.objects.create(
                notification=notification,
                user=recipient
            )