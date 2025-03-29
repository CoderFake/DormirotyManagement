from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from accounts.models import User
from dormitory.models import Room, Building


class MaintenanceCategory(models.Model):
    """Mô hình danh mục bảo trì"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên danh mục'), max_length=100)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    icon = models.CharField(_('biểu tượng'), max_length=50, blank=True, null=True)
    average_time = models.PositiveIntegerField(_('thời gian trung bình (giờ)'), default=24)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('danh mục bảo trì')
        verbose_name_plural = _('danh mục bảo trì')
        ordering = ['name']

    def __str__(self):
        return self.name


class MaintenanceRequest(models.Model):
    """Mô hình yêu cầu bảo trì"""

    PRIORITY_CHOICES = (
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    )

    STATUS_CHOICES = (
        ('pending', 'Chờ xử lý'),
        ('assigned', 'Đã phân công'),
        ('in_progress', 'Đang xử lý'),
        ('completed', 'Hoàn thành'),
        ('canceled', 'Đã hủy'),
        ('rejected', 'Từ chối'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_number = models.CharField(_('số yêu cầu'), max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_requests',
                             verbose_name=_('người yêu cầu'))
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='maintenance_requests',
                             verbose_name=_('phòng'))
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='maintenance_requests',
                                 verbose_name=_('tòa nhà'))
    category = models.ForeignKey(MaintenanceCategory, on_delete=models.CASCADE, related_name='maintenance_requests',
                                 verbose_name=_('danh mục'))
    title = models.CharField(_('tiêu đề'), max_length=255)
    description = models.TextField(_('mô tả'))
    priority = models.CharField(_('mức độ ưu tiên'), max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_date = models.DateTimeField(_('ngày yêu cầu'), default=timezone.now)
    scheduled_date = models.DateTimeField(_('ngày dự kiến'), null=True, blank=True)
    completed_date = models.DateTimeField(_('ngày hoàn thành'), null=True, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_maintenance_requests',
                                    verbose_name=_('người được phân công'), null=True, blank=True)
    admin_notes = models.TextField(_('ghi chú của quản trị viên'), blank=True, null=True)
    images = models.ImageField(_('hình ảnh'), upload_to='maintenance/', blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('yêu cầu bảo trì')
        verbose_name_plural = _('yêu cầu bảo trì')
        ordering = ['-requested_date']

    def __str__(self):
        return f"{self.request_number} - {self.title} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.request_number:
            year = timezone.now().strftime("%Y")
            month = timezone.now().strftime("%m")
            count = MaintenanceRequest.objects.filter(created_at__year=timezone.now().year).count() + 1
            self.request_number = f"MR-{year}{month}-{count:04d}"

        if self.room and not self.building:
            self.building = self.room.building

        super().save(*args, **kwargs)

    def assign_staff(self, staff_user):
        self.assigned_to = staff_user
        self.status = 'assigned'
        self.save()

    def start_progress(self):
        self.status = 'in_progress'
        self.save()

    def complete(self):
        self.status = 'completed'
        self.completed_date = timezone.now()
        self.save()

    def cancel(self):
        self.status = 'canceled'
        self.save()

    def reject(self, notes=None):
        self.status = 'rejected'
        if notes:
            self.admin_notes = notes
        self.save()


class MaintenanceComment(models.Model):
    """Mô hình bình luận về yêu cầu bảo trì"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE, related_name='comments',
                                            verbose_name=_('yêu cầu bảo trì'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_comments',
                             verbose_name=_('người bình luận'))
    comment = models.TextField(_('bình luận'))
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('bình luận bảo trì')
        verbose_name_plural = _('bình luận bảo trì')
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class MaintenanceImage(models.Model):
    """Mô hình hình ảnh cho yêu cầu bảo trì"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    maintenance_request = models.ForeignKey(MaintenanceRequest, on_delete=models.CASCADE,
                                            related_name='maintenance_images', verbose_name=_('yêu cầu bảo trì'))
    image = models.ImageField(_('hình ảnh'), upload_to='maintenance/')
    caption = models.CharField(_('chú thích'), max_length=255, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='maintenance_images',
                                    verbose_name=_('người tải lên'))
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)

    class Meta:
        verbose_name = _('hình ảnh bảo trì')
        verbose_name_plural = _('hình ảnh bảo trì')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.maintenance_request.request_number} - {self.caption or 'Hình ảnh'}"