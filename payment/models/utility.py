# payment/models/utility.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from decimal import Decimal
from dormitory.models import Room
from .base import Invoice


class ElectricityReading(models.Model):
    """Mô hình chỉ số điện"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='electricity_readings',
                             verbose_name=_('phòng'))
    month = models.PositiveSmallIntegerField(_('tháng'))
    year = models.PositiveSmallIntegerField(_('năm'))
    reading_date = models.DateField(_('ngày ghi'))
    previous_reading = models.PositiveIntegerField(_('chỉ số cũ'))
    current_reading = models.PositiveIntegerField(_('chỉ số mới'))
    unit_price = models.DecimalField(_('đơn giá'), max_digits=10, decimal_places=2)
    amount = models.DecimalField(_('thành tiền'), max_digits=10, decimal_places=2, default=0)
    is_billed = models.BooleanField(_('đã lập hóa đơn'), default=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, related_name='electricity_readings',
                                verbose_name=_('hóa đơn'), null=True, blank=True)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('chỉ số điện')
        verbose_name_plural = _('chỉ số điện')
        ordering = ['-year', '-month']
        unique_together = ('room', 'month', 'year')

    def __str__(self):
        return f"{self.room} - {self.month}/{self.year} - {self.get_usage()} kWh"

    def get_usage(self):
        return max(0, self.current_reading - self.previous_reading)

    def save(self, *args, **kwargs):
        usage = self.get_usage()
        self.amount = usage * self.unit_price

        super().save(*args, **kwargs)


class WaterReading(models.Model):
    """Mô hình chỉ số nước"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='water_readings', verbose_name=_('phòng'))
    month = models.PositiveSmallIntegerField(_('tháng'))
    year = models.PositiveSmallIntegerField(_('năm'))
    reading_date = models.DateField(_('ngày ghi'))
    previous_reading = models.PositiveIntegerField(_('chỉ số cũ'))
    current_reading = models.PositiveIntegerField(_('chỉ số mới'))
    unit_price = models.DecimalField(_('đơn giá'), max_digits=10, decimal_places=2)
    amount = models.DecimalField(_('thành tiền'), max_digits=10, decimal_places=2, default=0)
    is_billed = models.BooleanField(_('đã lập hóa đơn'), default=False)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, related_name='water_readings',
                                verbose_name=_('hóa đơn'), null=True, blank=True)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('chỉ số nước')
        verbose_name_plural = _('chỉ số nước')
        ordering = ['-year', '-month']
        unique_together = ('room', 'month', 'year')

    def __str__(self):
        return f"{self.room} - {self.month}/{self.year} - {self.get_usage()} m³"

    def get_usage(self):
        return max(0, self.current_reading - self.previous_reading)

    def save(self, *args, **kwargs):
        usage = self.get_usage()
        self.amount = usage * self.unit_price

        super().save(*args, **kwargs)
