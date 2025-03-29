from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    """Trình quản lý tùy chỉnh cho mô hình User"""

    def create_user(self, email, password=None, **extra_fields):
        """Tạo và lưu người dùng thông thường với email và mật khẩu đã cho"""
        if not email:
            raise ValueError(_('Email là bắt buộc'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Tạo và lưu người dùng quản trị với email và mật khẩu đã cho"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser phải có is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser phải có is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Mô hình User tùy chỉnh cho hệ thống Quản lý Ký túc xá"""

    USER_TYPE_CHOICES = (
        ('student', 'Sinh viên'),
        ('staff', 'Nhân viên'),
        ('admin', 'Quản trị viên'),
    )

    GENDER_CHOICES = (
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('other', 'Khác'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('địa chỉ email'), unique=True)
    username = models.CharField(_('tên người dùng'), max_length=150, blank=True, null=True)
    full_name = models.CharField(_('họ và tên'), max_length=255)
    student_id = models.CharField(_('mã sinh viên'), max_length=20, blank=True, null=True)
    phone_number = models.CharField(_('số điện thoại'), max_length=15, blank=True, null=True)
    address = models.TextField(_('địa chỉ'), blank=True, null=True)
    date_of_birth = models.DateField(_('ngày sinh'), blank=True, null=True)
    gender = models.CharField(_('giới tính'), max_length=10, choices=GENDER_CHOICES, default='male')
    id_card_number = models.CharField(_('số CMND/CCCD'), max_length=20, blank=True, null=True)
    university = models.CharField(_('trường đại học'), max_length=255, blank=True, null=True)
    faculty = models.CharField(_('khoa'), max_length=255, blank=True, null=True)
    avatar = models.ImageField(_('ảnh đại diện'), upload_to='avatars/', blank=True, null=True)
    user_type = models.CharField(_('loại người dùng'), max_length=10, choices=USER_TYPE_CHOICES, default='student')

    date_joined = models.DateTimeField(_('ngày tham gia'), default=timezone.now)
    last_login = models.DateTimeField(_('lần đăng nhập cuối'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    is_staff = models.BooleanField(_('nhân viên'), default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = _('người dùng')
        verbose_name_plural = _('người dùng')

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        names = self.full_name.split()
        return names[-1] if names else self.email.split('@')[0]


class PasswordReset(models.Model):
    """Mô hình để lưu trữ mã đặt lại mật khẩu"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets',
                             verbose_name=_('người dùng'))
    token = models.CharField(_('mã token'), max_length=100, unique=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    expires_at = models.DateTimeField(_('thời gian hết hạn'))
    is_used = models.BooleanField(_('đã sử dụng'), default=False)

    class Meta:
        verbose_name = _('đặt lại mật khẩu')
        verbose_name_plural = _('đặt lại mật khẩu')

    def __str__(self):
        return f"{self.user.email} - {self.token}"

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class UserProfile(models.Model):
    """Thông tin thêm về người dùng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('người dùng'))
    parent_name = models.CharField(_('tên phụ huynh'), max_length=255, blank=True, null=True)
    parent_phone = models.CharField(_('số điện thoại phụ huynh'), max_length=15, blank=True, null=True)
    emergency_contact = models.CharField(_('liên hệ khẩn cấp'), max_length=255, blank=True, null=True)
    emergency_phone = models.CharField(_('số điện thoại khẩn cấp'), max_length=15, blank=True, null=True)
    home_town = models.CharField(_('quê quán'), max_length=255, blank=True, null=True)
    bio = models.TextField(_('giới thiệu bản thân'), blank=True, null=True)
    facebook_url = models.URLField(_('liên kết Facebook'), blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('hồ sơ người dùng')
        verbose_name_plural = _('hồ sơ người dùng')

    def __str__(self):
        return f"Hồ sơ của {self.user.get_full_name()}"