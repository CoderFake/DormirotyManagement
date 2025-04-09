from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from .models import Contract
from payment.models import Invoice, InvoiceItem, FeeType
from .models import RoomRegistration, NotificationCategory, Notification, UserNotification


@receiver(pre_save, sender=Contract)
def handle_contract_status_change(sender, instance, **kwargs):
    """Handle contract status changes"""
    if instance._state.adding:
        return 
    
    try:
        old_instance = Contract.objects.get(pk=instance.pk)
    except Contract.DoesNotExist:
        return

    if old_instance.status == 'draft' and instance.status == 'active':
        context = {
            'contract': instance,
            'site_name': settings.SITE_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'support_phone': settings.SUPPORT_PHONE,
            'support_address': settings.SUPPORT_ADDRESS,
            'deposit_url': settings.BASE_URL + reverse('payment:deposit_payment', args=[instance.id])
        }
        
        html_message = render_to_string('registration/email/contract_approved.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'[{settings.SITE_NAME}] Hợp đồng của bạn đã được phê duyệt',
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            fail_silently=False
        )
    
    elif old_instance.status == 'active' and instance.status == 'cancelled':
        context = {
            'contract': instance,
            'site_name': settings.SITE_NAME,
            'support_email': settings.SUPPORT_EMAIL,
            'support_phone': settings.SUPPORT_PHONE,
            'support_address': settings.SUPPORT_ADDRESS
        }
        
        html_message = render_to_string('registration/email/contract_cancelled.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=f'[{settings.SITE_NAME}] Hợp đồng của bạn đã bị hủy',
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.user.email],
            fail_silently=False
        )


@receiver(post_save, sender=Contract)
def create_deposit_invoice(sender, instance, created, **kwargs):
    """Create deposit invoice when contract is created"""
    if created and instance.deposit_amount > 0:
        # Create deposit invoice
        invoice = Invoice.objects.create(
            user=instance.user,
            contract=instance,
            room=instance.room,
            due_date=timezone.now().date() + timezone.timedelta(days=7),
            total_amount=instance.deposit_amount,
            status='pending'
        )
        
        # Create deposit fee type if not exists
        fee_type, _ = FeeType.objects.get_or_create(
            code='DEPOSIT',
            defaults={
                'name': 'Tiền đặt cọc',
                'description': 'Tiền đặt cọc ký túc xá',
                'is_recurring': False
            }
        )
        
        # Create invoice item
        InvoiceItem.objects.create(
            invoice=invoice,
            fee_type=fee_type,
            description='Tiền đặt cọc ký túc xá',
            quantity=1,
            unit_price=instance.deposit_amount,
            amount=instance.deposit_amount
        )


@receiver(post_save, sender=Invoice)
def handle_deposit_payment(sender, instance, **kwargs):
    """Handle deposit payment completion"""
    if instance.contract and instance.contract.status == 'draft' and instance.status == 'paid':
        # If this is a deposit invoice and it's fully paid, activate the contract
        instance.contract.status = 'active'
        instance.contract.save()


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

    # Chỉ xử lý thông báo khi đơn bị từ chối, trạng thái 'approved' đã được xử lý trong view
    elif not created and 'status' in kwargs.get('update_fields', []) and instance.status == 'rejected':
        notification = Notification.objects.create(
            title="Đơn đăng ký phòng bị từ chối",
            content=f"Đơn đăng ký phòng của bạn đã bị từ chối. Lý do: {instance.admin_notes or 'Không có lý do cụ thể.'}",
            category=category,
            sender_id=None, # Cần xem xét lại nếu muốn hiển thị người từ chối
            priority="high",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )
