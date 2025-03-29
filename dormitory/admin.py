from django.contrib import admin
from .models import Building, RoomType, Room, Bed, Amenity, RoomAmenity


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'floors', 'is_active', 'get_total_rooms', 'get_available_rooms')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'address')

    def get_total_rooms(self, obj):
        return obj.get_total_rooms()

    get_total_rooms.short_description = 'Tổng số phòng'

    def get_available_rooms(self, obj):
        return obj.get_available_rooms()

    get_available_rooms.short_description = 'Phòng còn trống'


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'capacity', 'area', 'price_per_month', 'gender_allowed')
    list_filter = ('capacity', 'gender_allowed')
    search_fields = ('name', 'code', 'description')


class BedInline(admin.TabularInline):
    model = Bed
    extra = 1


class RoomAmenityInline(admin.TabularInline):
    model = RoomAmenity
    extra = 1


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'building', 'room_type', 'floor', 'status', 'current_occupancy', 'is_active')
    list_filter = ('building', 'room_type', 'floor', 'status', 'is_active')
    search_fields = ('room_number', 'building__name', 'description')
    inlines = [BedInline, RoomAmenityInline]

    def get_inline_instances(self, request, obj=None):
        if not obj:  # Khi tạo mới, không hiển thị inlines
            return []
        return super().get_inline_instances(request, obj)


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'room', 'bed_number', 'status', 'is_active')
    list_filter = ('room__building', 'status', 'is_active')
    search_fields = ('bed_number', 'room__room_number', 'room__building__name')


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon')
    search_fields = ('name', 'description')


@admin.register(RoomAmenity)
class RoomAmenityAdmin(admin.ModelAdmin):
    list_display = ('room', 'amenity', 'quantity')
    list_filter = ('amenity', 'room__building')
    search_fields = ('room__room_number', 'amenity__name')