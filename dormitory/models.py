from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class Building(models.Model):
    """Mô hình tòa nhà ký túc xá"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên tòa nhà'), max_length=100)
    code = models.CharField(_('mã tòa nhà'), max_length=10, unique=True)
    address = models.TextField(_('địa chỉ'), blank=True, null=True)
    floors = models.PositiveIntegerField(_('số tầng'), default=1)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    image = models.ImageField(_('hình ảnh'), upload_to='buildings/', blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('tòa nhà')
        verbose_name_plural = _('tòa nhà')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_total_rooms(self):
        return self.rooms.count()

    def get_available_rooms(self):
        return self.rooms.filter(status='available').count()


class RoomType(models.Model):
    """Mô hình loại phòng"""

    GENDER_CHOICES = (
        ('male', 'Nam'),
        ('female', 'Nữ'),
        ('mixed', 'Nam và Nữ'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên loại phòng'), max_length=100)
    code = models.CharField(_('mã loại phòng'), max_length=10, unique=True)
    capacity = models.PositiveIntegerField(_('sức chứa'), default=1)
    area = models.FloatField(_('diện tích (m²)'), default=0)
    amenities = models.TextField(_('tiện nghi'), blank=True, null=True)
    price_per_month = models.DecimalField(_('giá/tháng'), max_digits=10, decimal_places=2, default=0)
    deposit = models.DecimalField(_('tiền đặt cọc'), max_digits=10, decimal_places=2, default=0)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    image = models.ImageField(_('hình ảnh'), upload_to='room_types/', blank=True, null=True)
    gender_allowed = models.CharField(_('giới tính cho phép'), max_length=10, choices=GENDER_CHOICES, default='mixed')
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('loại phòng')
        verbose_name_plural = _('loại phòng')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.capacity} người - {self.price_per_month} VNĐ/tháng"


class Room(models.Model):
    """Mô hình phòng ký túc xá"""

    STATUS_CHOICES = (
        ('available', 'Còn trống'),
        ('partially_occupied', 'Còn chỗ'),
        ('fully_occupied', 'Đã đầy'),
        ('reserved', 'Đã đặt trước'),
        ('maintenance', 'Đang bảo trì'),
        ('unavailable', 'Không có sẵn'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name='rooms', verbose_name=_('tòa nhà'))
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms',
                                  verbose_name=_('loại phòng'))
    room_number = models.CharField(_('số phòng'), max_length=10)
    floor = models.PositiveIntegerField(_('tầng'), default=1)
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES, default='available')
    current_occupancy = models.PositiveIntegerField(_('số người hiện tại'), default=0)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    image = models.ImageField(_('hình ảnh'), upload_to='rooms/', blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('phòng')
        verbose_name_plural = _('phòng')
        ordering = ['building__name', 'floor', 'room_number']
        unique_together = ('building', 'room_number')

    def __str__(self):
        return f"{self.building.code}-{self.room_number} (Tầng {self.floor})"

    def save(self, *args, **kwargs):
        # Cập nhật trạng thái dựa trên số người hiện tại
        capacity = self.room_type.capacity
        if self.current_occupancy == 0:
            self.status = 'available'
        elif self.current_occupancy < capacity:
            self.status = 'partially_occupied'
        elif self.current_occupancy >= capacity:
            self.status = 'fully_occupied'

        super().save(*args, **kwargs)

    def get_available_beds(self):
        capacity = self.room_type.capacity
        return max(0, capacity - self.current_occupancy)


class Bed(models.Model):
    """Mô hình giường trong phòng"""

    STATUS_CHOICES = (
        ('available', 'Còn trống'),
        ('occupied', 'Đã có người'),
        ('reserved', 'Đã đặt trước'),
        ('maintenance', 'Đang bảo trì'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds', verbose_name=_('phòng'))
    bed_number = models.CharField(_('số giường'), max_length=10)
    status = models.CharField(_('trạng thái'), max_length=20, choices=STATUS_CHOICES, default='available')
    description = models.TextField(_('mô tả'), blank=True, null=True)
    is_active = models.BooleanField(_('đang hoạt động'), default=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('giường')
        verbose_name_plural = _('giường')
        ordering = ['room', 'bed_number']
        unique_together = ('room', 'bed_number')

    def __str__(self):
        return f"{self.room} - Giường {self.bed_number}"


class Amenity(models.Model):
    """Mô hình tiện nghi phòng"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tên tiện nghi'), max_length=100)
    description = models.TextField(_('mô tả'), blank=True, null=True)
    icon = models.CharField(_('biểu tượng'), max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('tiện nghi')
        verbose_name_plural = _('tiện nghi')
        ordering = ['name']

    def __str__(self):
        return self.name


class RoomAmenity(models.Model):
    """Mô hình liên kết phòng và tiện nghi"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_amenities', verbose_name=_('phòng'))
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE, related_name='room_amenities',
                                verbose_name=_('tiện nghi'))
    quantity = models.PositiveIntegerField(_('số lượng'), default=1)
    notes = models.TextField(_('ghi chú'), blank=True, null=True)
    created_at = models.DateTimeField(_('thời gian tạo'), auto_now_add=True)
    updated_at = models.DateTimeField(_('thời gian cập nhật'), auto_now=True)

    class Meta:
        verbose_name = _('tiện nghi phòng')
        verbose_name_plural = _('tiện nghi phòng')
        unique_together = ('room', 'amenity')

    def __str__(self):
        return f"{self.room} - {self.amenity} ({self.quantity})"