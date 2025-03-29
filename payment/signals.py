from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Invoice, Payment, ElectricityReading, WaterReading, VNPayTransaction
from notification.models import Notification, NotificationCategory, UserNotification


@receiver(post_save, sender=Invoice)
def create_invoice_notification(sender, instance, created, **kwargs):
    """Tạo thông báo khi có hóa đơn mới hoặc hóa đơn sắp đến hạn"""
    if created:
        category, _ = NotificationCategory.objects.get_or_create(
            name="Hóa đơn",
            defaults={
                'icon': 'fa-file-invoice-dollar',
                'color': 'primary',
                'description': 'Thông báo về hóa đơn thanh toán'
            }
        )

        notification = Notification.objects.create(
            title=f"Hóa đơn mới #{instance.invoice_number}",
            content=f"Bạn có hóa đơn mới cần thanh toán. Số tiền: {instance.total_amount:,} VNĐ. Hạn thanh toán: {instance.due_date.strftime('%d/%m/%Y')}",
            category=category,
            sender_id=None,
            priority="normal",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )

    elif instance.status == 'overdue' and kwargs.get('update_fields') and 'status' in kwargs.get('update_fields'):
        category, _ = NotificationCategory.objects.get_or_create(
            name="Hóa đơn quá hạn",
            defaults={
                'icon': 'fa-exclamation-circle',
                'color': 'danger',
                'description': 'Thông báo về hóa đơn quá hạn thanh toán'
            }
        )

        notification = Notification.objects.create(
            title=f"Hóa đơn #{instance.invoice_number} đã quá hạn",
            content=f"Hóa đơn #{instance.invoice_number} đã quá hạn thanh toán. Vui lòng thanh toán ngay để tránh phát sinh phí phạt. Số tiền còn thiếu: {instance.get_remaining_amount():,} VNĐ.",
            category=category,
            sender_id=None,
            priority="high",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )


@receiver(post_save, sender=Payment)
def update_invoice_after_payment(sender, instance, created, **kwargs):
    """Cập nhật trạng thái hóa đơn sau khi thanh toán và tạo thông báo"""
    if created:
        invoice = instance.invoice
        invoice.paid_amount += instance.amount
        invoice.save(update_fields=['paid_amount', 'status'])

        category, _ = NotificationCategory.objects.get_or_create(
            name="Thanh toán",
            defaults={
                'icon': 'fa-credit-card',
                'color': 'success',
                'description': 'Thông báo về thanh toán'
            }
        )

        notification = Notification.objects.create(
            title=f"Thanh toán hóa đơn #{invoice.invoice_number} thành công",
            content=f"Bạn đã thanh toán thành công số tiền {instance.amount:,} VNĐ cho hóa đơn #{invoice.invoice_number}. {('Số tiền còn thiếu: ' + str(invoice.get_remaining_amount()) + ' VNĐ.') if invoice.status != 'paid' else 'Hóa đơn đã được thanh toán đầy đủ.'}",
            category=category,
            sender_id=None,
            priority="normal",
            is_global=False,
        )

        UserNotification.objects.create(
            notification=notification,
            user=instance.user
        )


@receiver(post_save, sender=VNPayTransaction)
def update_payment_after_transaction(sender, instance, created, **kwargs):
    """Cập nhật trạng thái thanh toán sau khi giao dịch VNPay hoàn tất"""
    if not created and instance.transaction_status == 'success' and instance.payment:
        payment = instance.payment
        if payment.status != 'completed':
            payment.status = 'completed'
            payment.transaction_id = instance.transaction_no
            payment.payment_date = instance.transaction_date or timezone.now()
            payment.save(update_fields=['status', 'transaction_id', 'payment_date'])


@receiver(post_save, sender=ElectricityReading)
def create_electric_invoice_item(sender, instance, created, **kwargs):
    """Tạo mục hóa đơn từ chỉ số điện"""
    if instance.is_billed is False and instance.amount > 0:
        from .models import FeeType, Invoice, InvoiceItem
        fee_type, _ = FeeType.objects.get_or_create(
            code='ELECTRIC',
            defaults={
                'name': 'Tiền điện',
                'description': 'Phí tiền điện hàng tháng',
                'is_recurring': True,
                'is_active': True
            }
        )

        contracts = instance.room.contracts.filter(
            status='active',
            start_date__lte=timezone.now().date()
        )

        if contracts.exists():
            for contract in contracts:
                invoice, created = Invoice.objects.get_or_create(
                    user=contract.user,
                    month=instance.month,
                    year=instance.year,
                    defaults={
                        'room': instance.room,
                        'issue_date': timezone.now().date(),
                        'due_date': timezone.now().date() + timezone.timedelta(days=15),
                        'status': 'pending'
                    }
                )

                amount_per_person = instance.amount / max(1, instance.room.current_occupancy)
                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=fee_type,
                    description=f"Tiền điện tháng {instance.month}/{instance.year} (Chỉ số: {instance.previous_reading} - {instance.current_reading} = {instance.get_usage()} kWh)",
                    quantity=1,
                    unit_price=amount_per_person,
                    amount=amount_per_person
                )

            instance.is_billed = True
            instance.save(update_fields=['is_billed'])


@receiver(post_save, sender=WaterReading)
def create_water_invoice_item(sender, instance, created, **kwargs):
    """Tạo mục hóa đơn từ chỉ số nước"""
    if instance.is_billed is False and instance.amount > 0:
        from .models import FeeType, Invoice, InvoiceItem
        fee_type, _ = FeeType.objects.get_or_create(
            code='WATER',
            defaults={
                'name': 'Tiền nước',
                'description': 'Phí tiền nước hàng tháng',
                'is_recurring': True,
                'is_active': True
            }
        )

        contracts = instance.room.contracts.filter(
            status='active',
            start_date__lte=timezone.now().date()
        )

        if contracts.exists():
            for contract in contracts:
                invoice, created = Invoice.objects.get_or_create(
                    user=contract.user,
                    month=instance.month,
                    year=instance.year,
                    defaults={
                        'room': instance.room,
                        'issue_date': timezone.now().date(),
                        'due_date': timezone.now().date() + timezone.timedelta(days=15),
                        'status': 'pending'
                    }
                )

                amount_per_person = instance.amount / max(1, instance.room.current_occupancy)
                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=fee_type,
                    description=f"Tiền nước tháng {instance.month}/{instance.year} (Chỉ số: {instance.previous_reading} - {instance.current_reading} = {instance.get_usage()} m³)",
                    quantity=1,
                    unit_price=amount_per_person,
                    amount=amount_per_person
                )

            instance.is_billed = True
            instance.save(update_fields=['is_billed'])