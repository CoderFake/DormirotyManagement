from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

app_name = 'accounts'

urlpatterns = [
    # Xác thực người dùng
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Đặt lại mật khẩu
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'),
         name='password_reset_done'
         ),

    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),

    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'),
         name='password_reset_complete'
         ),

    # Hồ sơ người dùng
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('settings/', views.settings_view, name='settings'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('verify-email-confirm/<uidb64>/<token>/', views.verify_email_confirm_view, name='verify_email_confirm'),

    # Quản lý người dùng (Admin)
    path('admin/students/', views.student_list_view, name='student_list'),
    path('admin/students/<uuid:user_id>/', views.student_detail_view, name='student_detail'),
    path('admin/students/<uuid:user_id>/edit/', views.student_edit_view, name='student_edit'),
    path('admin/students/<uuid:user_id>/delete/', views.student_delete_view, name='student_delete'),

    path('admin/staff/', views.staff_list_view, name='staff_list'),
    path('admin/staff/<uuid:user_id>/', views.staff_detail_view, name='staff_detail'),
    path('admin/staff/<uuid:user_id>/edit/', views.staff_edit_view, name='staff_edit'),
    path('admin/staff/<uuid:user_id>/delete/', views.staff_delete_view, name='staff_delete'),

    path('admin/create/', views.user_create_view, name='user_create'),
]