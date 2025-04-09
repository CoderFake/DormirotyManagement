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


@receiver(pre_save, sender=Contract)
def handle_contract_status_change(sender, instance, **kwargs):
    """Handle contract status changes"""
    if not instance.pk:  # New contract
        return
    
    old_instance = Contract.objects.get(pk=instance.pk)
    
    # If status changed from draft to active
    if old_instance.status == 'draft' and instance.status == 'active':
        # Send approval email
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
    
    # If status changed from active to cancelled
    elif old_instance.status == 'active' and instance.status == 'cancelled':
        # Send cancellation email
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
