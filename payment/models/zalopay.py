from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class ZaloPayTransaction(models.Model):
    """Mô hình giao dịch ZaloPay"""

    STATUS_CHOICES = (
        ('pending', 'Đang xử lý'),
        ('success', 'Thành công'),
        ('failed', 'Thất bại'),
        ('canceled', 'Đã hủy'),
        ('refunded', 'Đã hoàn tiền'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='zalopay_transactions',
                             verbose_name=_('người dùng'))
    payment = models.OneToOneField('payment.Payment', on_delete=models.CASCADE, related_name='zalopay_transaction',
                                   verbose_name=_('thanh toán'), null=True, blank=True)
    amount = models.DecimalField(_('số tiền'), max_digits=10, decimal_places=2)
    order_info = models.CharField(_('thông tin đơn hàng'), max_length=255)
    app_trans_id = models.CharField(_('mã giao dịch ZaloPay'), max_length=100, unique=True)
    zp_trans_id = models.CharField(_('mã giao dịch ZaloPay'), max_length=100, blank=True, null=True)
    transaction_status = models.CharField(_('trạng thái giao dịch'), max_length=20, choices=STATUS_CHOICES,
                                          default='pending')
    transaction_date = models.DateTimeField(_('thời gian giao dịch'), blank=True, null=True)
    response_code = models.CharField(_('mã phản hồi'), max_length=10, blank=True, null=True)
    response_message = models.CharField(_('thông báo phản hồi'), max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('giao dịch ZaloPay')
        verbose_name_plural = _('giao dịch ZaloPay')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.amount} VNĐ - {self.get_transaction_status_display()}"
