from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from payment.models import Payment
import uuid


class VNPayTransaction(models.Model):
    """Mô hình giao dịch VNPay"""

    STATUS_CHOICES = (
        ('pending', 'Đang xử lý'),
        ('success', 'Thành công'),
        ('failed', 'Thất bại'),
        ('canceled', 'Đã hủy'),
        ('refunded', 'Đã hoàn tiền'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vnpay_transactions',
                             verbose_name=_('người dùng'))
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='vnpay_transaction',
                                   verbose_name=_('thanh toán'), null=True, blank=True)
    amount = models.DecimalField(_('số tiền'), max_digits=10, decimal_places=2)
    order_info = models.CharField(_('thông tin đơn hàng'), max_length=255)
    transaction_no = models.CharField(_('mã giao dịch VNPay'), max_length=100, blank=True, null=True)
    transaction_status = models.CharField(_('trạng thái giao dịch'), max_length=20, choices=STATUS_CHOICES,
                                          default='pending')
    bank_code = models.CharField(_('mã ngân hàng'), max_length=20, blank=True, null=True)
    card_type = models.CharField(_('loại thẻ'), max_length=20, blank=True, null=True)
    txn_ref = models.CharField(_('mã tham chiếu'), max_length=100, unique=True)
    secure_hash = models.CharField(_('mã băm bảo mật'), max_length=255, blank=True, null=True)
    transaction_date = models.DateTimeField(_('thời gian giao dịch'), blank=True, null=True)
    response_code = models.CharField(_('mã phản hồi'), max_length=10, blank=True, null=True)
    response_message = models.CharField(_('thông báo phản hồi'), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('giao dịch VNPay')
        verbose_name_plural = _('giao dịch VNPay')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} VNĐ - {self.get_transaction_status_display()}"