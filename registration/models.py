from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from accounts.models import User
from dormitory.models import Room, Bed, RoomType, Building
from django.core.exceptions import ValidationError


class RegistrationPeriod(models.Model):
    """Mô hình kỳ đăng ký ở ký túc xá"""

    STATUS_CHOICES = (
        ('upcoming', 'Sắp diễn ra'),
        ('active', 'Đang diễn ra'),
        ('closed', 'Đã kết thúc'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên kỳ đăng ký'), max_length=255)
    academic_year = models.CharField(_('năm học'), max_length=20)
    semester = models.CharField(_('học kỳ'), max_length=20)
    registration_start = models.DateTimeField(_('thời gian bắt đầu đăng ký'))
    registration_end = models.DateTimeField(_('thời gian kết thúc đăng ký'))
    check_in_start = models.DateTimeField(_('thời gian bắt đầu nhận phòng'))
    check_in_end = models.DateTimeField(_('thời gian kết thúc nhận phòng'))
    contract_start = models.DateField(_('ngày bắt đầu hợp đồng'))
    contract_end = models.DateField(_('ngày kết thúc hợp đồng'))
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES, default='upcoming')
    description = models.TextField(_('mô tả'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('kỳ đăng ký')
        verbose_name_plural = _('kỳ đăng ký')
        ordering = ['-registration_start']

    def __str__(self):
        return f"{self.name} - {self.academic_year} - {self.semester}"

    def save(self, *args, **kwargs):
        # Cập nhật trạng thái dựa trên thời gian
        now = timezone.now()
        if now < self.registration_start:
            self.status = 'upcoming'
        elif self.registration_start <= now <= self.registration_end:
            self.status = 'active'
        else:
            self.status = 'closed'

        super().save(*args, **kwargs)


class RoomRegistration(models.Model):
    """Mô hình đăng ký phòng ở"""

    STATUS_CHOICES = (
        ('pending', 'Chờ xét duyệt'),
        ('approved', 'Đã duyệt'),
        ('rejected', 'Từ chối'),
        ('canceled', 'Đã hủy'),
        ('expired', 'Hết hạn'),
        ('confirmed', 'Đã xác nhận'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations', verbose_name=_('sinh viên'))
    registration_period = models.ForeignKey(RegistrationPeriod, on_delete=models.CASCADE, related_name='registrations',
                                            verbose_name=_('kỳ đăng ký'))
    preferred_building = models.ForeignKey(Building, on_delete=models.SET_NULL, related_name='registrations',
                                           verbose_name=_('tòa nhà mong muốn'), null=True, blank=True)
    preferred_room_type = models.ForeignKey(RoomType, on_delete=models.SET_NULL, related_name='registrations',
                                            verbose_name=_('loại phòng mong muốn'), null=True, blank=True)
    assigned_room = models.ForeignKey(Room, on_delete=models.SET_NULL, related_name='registrations',
                                      verbose_name=_('phòng được phân'), null=True, blank=True)
    assigned_bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, related_name='registrations',
                                     verbose_name=_('giường được phân'), null=True, blank=True)
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES, default='pending')
    registration_date = models.DateTimeField(_('ngày đăng ký'), auto_now_add=True)
    approval_date = models.DateTimeField(_('ngày duyệt'), null=True, blank=True)
    special_requirements = models.TextField(_('yêu cầu đặc biệt'), blank=True, null=True)
    admin_notes = models.TextField(_('ghi chú của admin'), blank=True, null=True)

    class Meta:
        verbose_name = _('đăng ký phòng')
        verbose_name_plural = _('đăng ký phòng')
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.registration_period} - {self.get_status_display()}"

    def clean(self):

        if self.registration_period and self.registration_period.status != 'active':
            raise ValidationError(_('Kỳ đăng ký này hiện không mở cho đăng ký.'))
        if self.user and self.registration_period:
            existing_reg = RoomRegistration.objects.filter(
                user=self.user,
                registration_period=self.registration_period,
                status__in=['pending', 'approved', 'confirmed']
            )
            if self.pk:
                existing_reg = existing_reg.exclude(pk=self.pk)
            if existing_reg.exists():
                raise ValidationError(_('Bạn đã đăng ký trong kỳ này rồi.'))

    def approve(self, assigned_room=None, assigned_bed=None):
        self.status = 'approved'
        self.approval_date = timezone.now()
        if assigned_room:
            self.assigned_room = assigned_room
        if assigned_bed:
            self.assigned_bed = assigned_bed
        self.save()

    def reject(self, notes=None):
        self.status = 'rejected'
        if notes:
            self.admin_notes = notes
        self.save()

    def cancel(self):
        self.status = 'canceled'
        self.save()

    def confirm(self):
        self.status = 'confirmed'
        self.save()


class Contract(models.Model):
    """Mô hình hợp đồng ở ký túc xá"""

    STATUS_CHOICES = (
        ('draft', 'Dự thảo'),
        ('pending_signature', 'Chờ sinh viên ký'),
        ('pending_payment', 'Chờ thanh toán cọc'),
        ('active', 'Đang hiệu lực'),
        ('terminated', 'Đã chấm dứt'),
        ('expired', 'Hết hạn'),
        ('canceled', 'Đã hủy'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract_number = models.CharField(_('số hợp đồng'), max_length=50, unique=True)
    registration = models.OneToOneField(RoomRegistration, on_delete=models.CASCADE, related_name='contract',
                                        verbose_name=_('đăng ký'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contracts', verbose_name=_('sinh viên'))
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, related_name='contracts', verbose_name=_('phòng'),
                             null=True)
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, related_name='contracts', verbose_name=_('giường'),
                            null=True)
    start_date = models.DateField(_('ngày bắt đầu'))
    end_date = models.DateField(_('ngày kết thúc'))
    monthly_fee = models.DecimalField(_('phí hàng tháng'), max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(_('tiền đặt cọc'), max_digits=10, decimal_places=2)
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES)
    signed_by_student = models.BooleanField(_('sinh viên đã ký'), default=False)
    student_signature = models.TextField(_('chữ ký sinh viên'), blank=True, null=True)
    signed_by_admin = models.BooleanField(_('quản trị viên đã ký'), default=False)
    student_signed_date = models.DateTimeField(_('ngày sinh viên ký'), null=True, blank=True)
    admin_signed_date = models.DateTimeField(_('ngày quản trị viên ký'), null=True, blank=True)
    terms_and_conditions = models.TextField(_('điều khoản và điều kiện'), blank=True, null=True)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('hợp đồng')
        verbose_name_plural = _('hợp đồng')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contract_number} - {self.user.get_full_name()} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.contract_number:
            year = timezone.now().strftime("%Y")
            month = timezone.now().strftime("%m")
            count = Contract.objects.filter(created_at__year=timezone.now().year).count()
            self.contract_number = f"HD-{year}{month}-{count + 1:04d}"

        super().save(*args, **kwargs)

    def sign_by_student(self, signature_data):
        self.signed_by_student = True
        self.student_signature = signature_data
        self.student_signed_date = timezone.now()
        if self.status == 'pending_signature':
            self.status = 'pending_payment'
        self.save(update_fields=['signed_by_student', 'student_signature', 'student_signed_date', 'status'])

    def activate_contract(self):
        if self.signed_by_student and self.status == 'pending_payment':
            today = timezone.now().date()
            if self.start_date <= today <= self.end_date:
                self.status = 'active'
            elif today < self.start_date:
                pass
            else:
                self.status = 'expired'
            self.save(update_fields=['status'])

    def terminate(self):
        if self.status != 'terminated':
            self.status = 'terminated'
            self.save(update_fields=['status'])

    def cancel(self):
        if self.status not in ['canceled', 'terminated', 'expired']:
            self.status = 'canceled'
            self.save(update_fields=['status'])

    def is_active(self):
        return self.status == 'active' and self.start_date <= timezone.now().date() <= self.end_date

    def get_duration_months(self):
        months = (self.end_date.year - self.start_date.year) * 12 + (self.end_date.month - self.start_date.month)
        if self.end_date.day >= self.start_date.day:
            months += 1
        return max(1, months)

    def get_total_amount(self):
        return self.monthly_fee * self.get_duration_months()

    def get_status_color(self):
        """Trả về màu sắc bootstrap tương ứng với trạng thái"""
        color_map = {
            'draft': 'secondary',
            'pending_signature': 'warning',
            'pending_payment': 'info',
            'active': 'success',
            'terminated': 'danger',
            'expired': 'dark',
            'canceled': 'secondary',
        }
        return color_map.get(self.status, 'secondary')
        
    def get_deposit_invoice(self):
        """Lấy hóa đơn đặt cọc liên quan đến hợp đồng này"""
        from payment.models import Invoice 
        try:
            deposit_invoice = Invoice.objects.filter(
                contract=self,
                invoice_items__fee_type__code='DEPOSIT'
            ).first()
            return deposit_invoice
        except Invoice.DoesNotExist:
            return None


class CheckIn(models.Model):
    """Mô hình nhận phòng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name='check_in',
                                    verbose_name=_('hợp đồng'))
    check_in_date = models.DateTimeField(_('ngày nhận phòng'), default=timezone.now)
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='check_ins_performed',
                                   verbose_name=_('nhân viên xác nhận'), null=True)
    room_condition = models.TextField(_('tình trạng phòng'), blank=True, null=True)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    items_received = models.TextField(_('đồ đạc đã nhận'), blank=True, null=True)
    is_completed = models.BooleanField(_('đã hoàn thành'), default=False)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('nhận phòng')
        verbose_name_plural = _('nhận phòng')
        ordering = ['-check_in_date']

    def __str__(self):
        return f"{self.contract.user.get_full_name()} - {self.check_in_date.strftime('%d/%m/%Y')}"


class CheckOut(models.Model):
    """Mô hình trả phòng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name='check_out',
                                    verbose_name=_('hợp đồng'))
    check_out_date = models.DateTimeField(_('ngày trả phòng'), default=timezone.now)
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='check_outs_performed',
                                   verbose_name=_('nhân viên xác nhận'), null=True)
    room_condition = models.TextField(_('tình trạng phòng'), blank=True, null=True)
    damage_description = models.TextField(_('mô tả hư hỏng'), blank=True, null=True)
    damage_charges = models.DecimalField(_('phí hư hỏng'), max_digits=10, decimal_places=2, default=0)
    deposit_refunded = models.DecimalField(_('tiền đặt cọc hoàn trả'), max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    is_completed = models.BooleanField(_('đã hoàn thành'), default=False)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('trả phòng')
        verbose_name_plural = _('trả phòng')
        ordering = ['-check_out_date']

    def __str__(self):
        return f"{self.contract.user.get_full_name()} - {self.check_out_date.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        deposit = self.contract.deposit_amount
        self.deposit_refunded = max(0, deposit - self.damage_charges)
        super().save(*args, **kwargs)