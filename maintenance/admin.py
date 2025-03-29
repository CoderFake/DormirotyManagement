from django.contrib import admin
from .models import MaintenanceCategory, MaintenanceRequest, MaintenanceComment, MaintenanceImage

@admin.register(MaintenanceCategory)
class MaintenanceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'average_time')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class MaintenanceCommentInline(admin.TabularInline):
    model = MaintenanceComment
    extra = 0
    readonly_fields = ('created_at', 'updated_at')


class MaintenanceImageInline(admin.TabularInline):
    model = MaintenanceImage
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'title', 'user', 'room', 'category', 'priority', 'status', 'requested_date')
    list_filter = ('status', 'priority', 'category', 'requested_date')
    search_fields = ('request_number', 'title', 'description', 'user__full_name', 'room__room_number')
    readonly_fields = ('request_number', 'requested_date', 'created_at', 'updated_at')
    date_hierarchy = 'requested_date'
    inlines = [MaintenanceCommentInline, MaintenanceImageInline]
    autocomplete_fields = ['user', 'room', 'building', 'category', 'assigned_to']

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('request_number', 'title', 'description', 'user', 'room', 'building', 'category', 'priority')
        }),
        ('Trạng thái và phân công', {
            'fields': ('status', 'assigned_to', 'scheduled_date', 'completed_date')
        }),
        ('Ghi chú và thông tin bổ sung', {
            'fields': ('admin_notes', 'requested_date', 'created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser or request.user.user_type == 'admin':
            return queryset
        elif request.user.user_type == 'staff':
            return queryset.filter(assigned_to=request.user) | queryset.filter(assigned_to__isnull=True)
        return queryset.none()


@admin.register(MaintenanceComment)
class MaintenanceCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'maintenance_request', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('maintenance_request__request_number', 'user__full_name', 'comment')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(MaintenanceImage)
class MaintenanceImageAdmin(admin.ModelAdmin):
    list_display = ('maintenance_request', 'caption', 'uploaded_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('maintenance_request__request_number', 'caption', 'uploaded_by__full_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'