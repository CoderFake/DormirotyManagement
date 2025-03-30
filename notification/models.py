from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
from accounts.models import User
from dormitory.models import Building, Room


class NotificationCategory(models.Model):
    """Mô hình danh mục thông báo"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên danh mục'), max_length=100)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    color = models.CharField(_('màu sắc'), max_length=20, default='primary')
    icon = models.CharField(_('biểu tượng'), max_length=50, blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('danh mục thông báo')
        verbose_name_plural = _('danh mục thông báo')
        ordering = ['name']

    def __str__(self):
        return self.name


class Notification(models.Model):
    """Mô hình thông báo"""

    PRIORITY_CHOICES = (
        ('low', 'Thấp'),
        ('normal', 'Bình thường'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('tiêu đề'), max_length=255)
    content = models.TextField(_('nội dung'))
    category = models.ForeignKey(NotificationCategory, on_delete=models.CASCADE, related_name='notifications',
                                 verbose_name=_('danh mục'))
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications',
                               verbose_name=_('người gửi'))
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    start_date = models.DateTimeField(_('ngày bắt đầu hiển thị'), default=timezone.now)
    end_date = models.DateTimeField(_('ngày kết thúc hiển thị'), null=True, blank=True)
    priority = models.CharField(_('mức độ ưu tiên'), max_length=10, choices=PRIORITY_CHOICES, default='normal')
    target_buildings = models.ManyToManyField(Building, blank=True, related_name='notifications',
                                              verbose_name=_('tòa nhà đích'))
    target_rooms = models.ManyToManyField(Room, blank=True, related_name='notifications', verbose_name=_('phòng đích'))
    is_global = models.BooleanField(_('gửi cho tất cả'), default=False)

    class Meta:
        verbose_name = _('thông báo')
        verbose_name_plural = _('thông báo')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class UserNotification(models.Model):
    """Mô hình liên kết thông báo và người dùng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='user_notifications',
                                     verbose_name=_('thông báo'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications',
                             verbose_name=_('người dùng'))
    is_read = models.BooleanField(_('đã đọc'), default=False)
    read_at = models.DateTimeField(_('thời gian đọc'), null=True, blank=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)

    class Meta:
        verbose_name = _('thông báo người dùng')
        verbose_name_plural = _('thông báo người dùng')
        ordering = ['-created_at']
        unique_together = ('notification', 'user')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.notification.title}"

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class Announcement(models.Model):
    """Mô hình thông báo chung"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('tiêu đề'), max_length=255)
    content = models.TextField(_('nội dung'))
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements', verbose_name=_('tác giả'))
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    start_date = models.DateTimeField(_('ngày bắt đầu hiển thị'), default=timezone.now)
    end_date = models.DateTimeField(_('ngày kết thúc hiển thị'), null=True, blank=True)
    is_pinned = models.BooleanField(_('ghim'), default=False)
    image = models.ImageField(_('hình ảnh'), upload_to='announcements/', blank=True, null=True)

    class Meta:
        verbose_name = _('thông báo chung')
        verbose_name_plural = _('thông báo chung')
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class NotificationSettings(models.Model):
    """Mô hình cài đặt thông báo cho người dùng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_settings',
                                verbose_name=_('người dùng'))
    category = models.ForeignKey(NotificationCategory, on_delete=models.CASCADE, related_name='user_settings',
                                 verbose_name=_('danh mục'))
    app_enabled = models.BooleanField(_('bật trong ứng dụng'), default=True)
    email_enabled = models.BooleanField(_('bật thông báo email'), default=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('cài đặt thông báo')
        verbose_name_plural = _('cài đặt thông báo')
        unique_together = ('user', 'category')

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.category.name}"

    @classmethod
    def get_settings_for_user(cls, user, category=None):
        if category:
            try:
                return cls.objects.get(user=user, category=category)
            except cls.DoesNotExist:
                return cls.objects.create(user=user, category=category)
        else:
            user_settings = {}
            categories = NotificationCategory.objects.all()
            for cat in categories:
                setting, created = cls.objects.get_or_create(user=user, category=cat)
                user_settings[cat.id] = setting
            return user_settings