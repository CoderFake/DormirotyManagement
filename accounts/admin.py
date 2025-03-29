from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, PasswordReset


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ'
    fk_name = 'user'


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'user_type', 'phone_number', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('email', 'full_name', 'student_id', 'phone_number')
    ordering = ('-date_joined',)
    filter_horizontal = ('groups', 'user_permissions',)
    readonly_fields = ('date_joined', 'last_login')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Thông tin cá nhân'), {'fields': (
            'full_name', 'student_id', 'phone_number', 'gender', 'date_of_birth',
            'address', 'id_card_number', 'university', 'faculty', 'avatar'
        )}),
        (_('Phân quyền'),
         {'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Thông tin hệ thống'), {'fields': ('date_joined', 'last_login')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'user_type', 'password1', 'password2'),
        }),
    )

    inlines = (UserProfileInline,)


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'expires_at', 'is_used')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email', 'token')
    readonly_fields = ('user', 'token', 'created_at', 'expires_at')

    def has_add_permission(self, request, obj=None):
        return False