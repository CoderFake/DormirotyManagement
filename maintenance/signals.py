from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import transaction

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

    with transaction.atomic():
        if created:
            notification = Notification.objects.create(
                title="Yêu cầu bảo trì đã được tạo",
                content=f"Yêu cầu bảo trì '{instance.title}' của bạn đã được ghi nhận và đang chờ xử lý. Mã yêu cầu: {instance.request_number}.",
                category=category,
                sender_id=None,
                priority="normal",
                is_global=False,
            )

            user_notification = UserNotification.objects.create(
                notification=notification,
                user=instance.user
            )

            try:
                subject = f"Yêu cầu bảo trì đã được tạo - {instance.request_number}"

                email_context = {
                    "user": instance.user,
                    "maintenance_request": instance,
                    "notification": notification,
                    "site_name": "Hệ thống Quản lý Ký túc xá",
                }

                html_message = render_to_string('maintenance/email/maintenance_created.html', email_context)

                email_message = EmailMessage(
                    subject=subject,
                    body=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[instance.user.email],
                )
                email_message.content_subtype = "html"
                email_message.send()
            except Exception as e:
                print(f"Lỗi khi gửi email thông báo bảo trì cho {instance.user.email}: {str(e)}")

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

                    if instance.priority in ['high', 'urgent']:
                        try:
                            subject = f"Yêu cầu bảo trì khẩn cấp mới - {instance.request_number}"

                            email_context = {
                                "admin": admin,
                                "maintenance_request": instance,
                                "notification": admin_notification,
                                "site_name": "Hệ thống Quản lý Ký túc xá",
                            }

                            html_message = render_to_string('maintenance/email/maintenance_admin_alert.html',
                                                            email_context)

                            email_message = EmailMessage(
                                subject=subject,
                                body=html_message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[admin.email],
                            )
                            email_message.content_subtype = "html"
                            email_message.send()
                        except Exception as e:
                            print(f"Lỗi khi gửi email thông báo bảo trì cho admin {admin.email}: {str(e)}")

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

                    try:
                        subject = f"Yêu cầu bảo trì đã được phân công - {instance.request_number}"

                        email_context = {
                            "user": instance.user,
                            "maintenance_request": instance,
                            "notification": notification,
                            "site_name": "Hệ thống Quản lý Ký túc xá",
                        }

                        html_message = render_to_string('maintenance/email/maintenance_assigned.html', email_context)

                        email_message = EmailMessage(
                            subject=subject,
                            body=html_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[instance.user.email],
                        )
                        email_message.content_subtype = "html"
                        email_message.send()
                    except Exception as e:
                        print(f"Lỗi khi gửi email thông báo bảo trì cho {instance.user.email}: {str(e)}")

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

                        try:
                            subject = f"Bạn được phân công xử lý yêu cầu bảo trì - {instance.request_number}"

                            email_context = {
                                "staff": instance.assigned_to,
                                "maintenance_request": instance,
                                "notification": staff_notification,
                                "site_name": "Hệ thống Quản lý Ký túc xá",
                            }

                            html_message = render_to_string('maintenance/email/maintenance_staff_assigned.html',
                                                            email_context)

                            email_message = EmailMessage(
                                subject=subject,
                                body=html_message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[instance.assigned_to.email],
                            )
                            email_message.content_subtype = "html"
                            email_message.send()
                        except Exception as e:
                            print(
                                f"Lỗi khi gửi email thông báo bảo trì cho nhân viên {instance.assigned_to.email}: {str(e)}")

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

                    try:
                        subject = f"Yêu cầu bảo trì đang được xử lý - {instance.request_number}"

                        email_context = {
                            "user": instance.user,
                            "maintenance_request": instance,
                            "notification": notification,
                            "site_name": "Hệ thống Quản lý Ký túc xá",
                        }

                        html_message = render_to_string('maintenance/email/maintenance_in_progress.html', email_context)

                        email_message = EmailMessage(
                            subject=subject,
                            body=html_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[instance.user.email],
                        )
                        email_message.content_subtype = "html"
                        email_message.send()
                    except Exception as e:
                        print(f"Lỗi khi gửi email thông báo bảo trì cho {instance.user.email}: {str(e)}")

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

                    try:
                        subject = f"Yêu cầu bảo trì đã hoàn thành - {instance.request_number}"

                        email_context = {
                            "user": instance.user,
                            "maintenance_request": instance,
                            "notification": notification,
                            "site_name": "Hệ thống Quản lý Ký túc xá",
                        }

                        html_message = render_to_string('maintenance/email/maintenance_completed.html', email_context)

                        email_message = EmailMessage(
                            subject=subject,
                            body=html_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[instance.user.email],
                        )
                        email_message.content_subtype = "html"
                        email_message.send()
                    except Exception as e:
                        # Log lỗi nhưng không dừng luồng xử lý
                        print(f"Lỗi khi gửi email thông báo bảo trì cho {instance.user.email}: {str(e)}")

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

                    try:
                        subject = f"Yêu cầu bảo trì bị từ chối - {instance.request_number}"

                        email_context = {
                            "user": instance.user,
                            "maintenance_request": instance,
                            "notification": notification,
                            "site_name": "Hệ thống Quản lý Ký túc xá",
                        }

                        html_message = render_to_string('maintenance/email/maintenance_rejected.html', email_context)

                        email_message = EmailMessage(
                            subject=subject,
                            body=html_message,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[instance.user.email],
                        )
                        email_message.content_subtype = "html"
                        email_message.send()
                    except Exception as e:
                        print(f"Lỗi khi gửi email thông báo bảo trì cho {instance.user.email}: {str(e)}")