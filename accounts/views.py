from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail, BadHeaderError
from django.http import HttpResponse
from django.db import transaction
from django.conf import settings
from django.utils import timezone
import uuid

from .forms import (
    UserLoginForm, UserRegistrationForm, CustomPasswordResetForm, CustomSetPasswordForm,
    CustomPasswordChangeForm, UserProfileForm, UserProfileExtendedForm,
    AdminUserCreateForm, AdminUserEditForm
)
from .models import User, UserProfile, PasswordReset


def login_view(request):
    """Xử lý đăng nhập người dùng"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')

            user = authenticate(username=email, password=password)
            if user is not None:
                login(request, user)

                user.last_login = timezone.now()
                user.save()

                if not remember_me:
                    request.session.set_expiry(0)

                next_page = request.GET.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect('dashboard:index')
    else:
        form = UserLoginForm()

    context = {
        'form': form,
        'page_title': 'Đăng nhập'
    }
    return render(request, 'accounts/login.html', context)


def logout_view(request):
    """Xử lý đăng xuất người dùng"""
    logout(request)
    messages.success(request, 'Bạn đã đăng xuất thành công.')
    return redirect('home')


def register_view(request):
    """Xử lý đăng ký tài khoản mới"""
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(user=user)

            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.email, password=raw_password)
            login(request, user)

            messages.success(request, 'Đăng ký tài khoản thành công! Chào mừng bạn đến với hệ thống Quản lý Ký túc xá.')
            return redirect('dashboard:index')
    else:
        form = UserRegistrationForm()

    context = {
        'form': form,
        'page_title': 'Đăng ký tài khoản'
    }
    return render(request, 'accounts/register.html', context)


@login_required
def verify_email_view(request):
    """Xác thực email người dùng"""
    if request.method == 'POST':
        user = request.user
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        verify_url = request.build_absolute_uri(
            f"/accounts/verify-email-confirm/{uid}/{token}/"
        )

        subject = "Xác thực email"
        email_template = "accounts/email_verification_email.html"
        email_context = {
            "user": user,
            "verify_url": verify_url,
            "site_name": "Hệ thống Quản lý Ký túc xá",
        }

        html_message = render_to_string(email_template, email_context)
        plain_message = render_to_string("accounts/email_verification_email.txt", email_context)

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            messages.success(request, 'Email xác thực đã được gửi. Vui lòng kiểm tra hộp thư của bạn.')
        except Exception as e:
            messages.error(request, f'Có lỗi khi gửi email: {str(e)}')

        return redirect('accounts:profile')

    context = {
        'page_title': 'Xác thực email',
        'breadcrumbs': [
            {'title': 'Tài khoản', 'url': '#'},
            {'title': 'Xác thực email', 'url': None}
        ]
    }
    return render(request, 'accounts/verify_email.html', context)


def verify_email_confirm_view(request, uidb64, token):
    """Xác nhận email từ link trong email"""
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_verified = True
        user.save()
        messages.success(request, 'Email của bạn đã được xác thực thành công. Bây giờ bạn có thể đăng nhập.')
        return redirect('accounts:login')
    else:
        messages.error(request, 'Link xác thực không hợp lệ hoặc đã hết hạn.')
        return redirect('accounts:login')


def password_reset_request(request):
    """Xử lý yêu cầu đặt lại mật khẩu"""
    if request.method == 'POST':
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            user = User.objects.filter(email=email).first()

            if user:
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                expiry_time = timezone.now() + timezone.timedelta(hours=24)
                password_reset = PasswordReset.objects.create(
                    user=user,
                    token=token,
                    expires_at=expiry_time
                )

                subject = "Yêu cầu đặt lại mật khẩu"
                reset_url = request.build_absolute_uri(
                    f"/accounts/password-reset-confirm/{uid}/{token}/"
                )

                email_template = "accounts/password_reset_email.html"
                email_context = {
                    "user": user,
                    "reset_url": reset_url,
                    "site_name": "Hệ thống Quản lý Ký túc xá",
                    "expiry_time": expiry_time
                }

                html_message = render_to_string(email_template, email_context)
                plain_message = render_to_string("accounts/password_reset_email.txt", email_context)

                try:
                    send_mail(
                        subject=subject,
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        html_message=html_message,
                        fail_silently=False
                    )
                    return redirect("accounts:password_reset_done")
                except BadHeaderError:
                    return HttpResponse("Đã xảy ra lỗi khi gửi email. Vui lòng thử lại sau.")

            return redirect("accounts:password_reset_done")
    else:
        form = CustomPasswordResetForm()

    context = {
        'form': form,
        'page_title': 'Đặt lại mật khẩu'
    }
    return render(request, 'accounts/password_reset.html', context)


@login_required
def profile_view(request):
    """Hiển thị thông tin hồ sơ người dùng"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    context = {
        'user': request.user,
        'profile': profile,
        'page_title': 'Hồ sơ của tôi',
        'breadcrumbs': [
            {'title': 'Hồ sơ', 'url': None}
        ]
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """Chỉnh sửa thông tin hồ sơ người dùng"""
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        user_form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        profile_form = UserProfileExtendedForm(request.POST, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()

            messages.success(request, 'Thông tin hồ sơ đã được cập nhật thành công.')
            return redirect('accounts:profile')
    else:
        user_form = UserProfileForm(instance=request.user)
        profile_form = UserProfileExtendedForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'page_title': 'Chỉnh sửa hồ sơ',
        'breadcrumbs': [
            {'title': 'Hồ sơ', 'url': reverse_lazy('accounts:profile')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def change_password_view(request):
    """Thay đổi mật khẩu người dùng"""
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Giữ người dùng đăng nhập
            messages.success(request, 'Mật khẩu của bạn đã được thay đổi thành công.')
            return redirect('accounts:profile')
    else:
        form = CustomPasswordChangeForm(request.user)

    context = {
        'form': form,
        'page_title': 'Thay đổi mật khẩu',
        'breadcrumbs': [
            {'title': 'Hồ sơ', 'url': reverse_lazy('accounts:profile')},
            {'title': 'Thay đổi mật khẩu', 'url': None}
        ]
    }
    return render(request, 'accounts/change_password.html', context)


@login_required
def settings_view(request):
    """Cài đặt tài khoản người dùng"""
    context = {
        'page_title': 'Cài đặt tài khoản',
        'breadcrumbs': [
            {'title': 'Cài đặt', 'url': None}
        ]
    }
    return render(request, 'accounts/settings.html', context)


def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'


def is_admin_or_staff(user):
    return user.is_authenticated and user.user_type in ['admin', 'staff']


@login_required
@user_passes_test(is_admin)
def student_list_view(request):
    """Danh sách sinh viên (cho Admin)"""
    students = User.objects.filter(user_type='student').order_by('-date_joined')

    context = {
        'students': students,
        'page_title': 'Danh sách sinh viên',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Sinh viên', 'url': None}
        ]
    }
    return render(request, 'accounts/student_list.html', context)


@login_required
@user_passes_test(is_admin)
def student_detail_view(request, user_id):
    """Chi tiết thông tin sinh viên (cho Admin)"""
    student = get_object_or_404(User, pk=user_id, user_type='student')

    try:
        profile = student.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=student)

    context = {
        'student': student,
        'profile': profile,
        'page_title': f'Thông tin sinh viên: {student.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Sinh viên', 'url': reverse_lazy('accounts:student_list')},
            {'title': student.full_name, 'url': None}
        ]
    }
    return render(request, 'accounts/student_detail.html', context)


@login_required
@user_passes_test(is_admin)
def student_edit_view(request, user_id):
    """Chỉnh sửa thông tin sinh viên (cho Admin)"""
    student = get_object_or_404(User, pk=user_id, user_type='student')

    try:
        profile = student.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=student)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=student)
        profile_form = UserProfileExtendedForm(request.POST, instance=profile)

        if form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                form.save()
                profile_form.save()

            messages.success(request, f'Thông tin sinh viên {student.full_name} đã được cập nhật thành công.')
            return redirect('accounts:student_detail', user_id=student.id)
    else:
        form = AdminUserEditForm(instance=student)
        profile_form = UserProfileExtendedForm(instance=profile)

    context = {
        'form': form,
        'profile_form': profile_form,
        'student': student,
        'page_title': f'Chỉnh sửa sinh viên: {student.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Sinh viên', 'url': reverse_lazy('accounts:student_list')},
            {'title': student.full_name,
             'url': reverse_lazy('accounts:student_detail', kwargs={'user_id': student.id})},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'accounts/student_edit.html', context)


@login_required
@user_passes_test(is_admin)
def student_delete_view(request, user_id):
    """Xóa sinh viên (cho Admin)"""
    student = get_object_or_404(User, pk=user_id, user_type='student')

    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        messages.success(request, f'Sinh viên {student_name} đã được xóa thành công.')
        return redirect('accounts:student_list')

    context = {
        'student': student,
        'page_title': f'Xóa sinh viên: {student.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Sinh viên', 'url': reverse_lazy('accounts:student_list')},
            {'title': student.full_name,
             'url': reverse_lazy('accounts:student_detail', kwargs={'user_id': student.id})},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'accounts/student_delete.html', context)


@login_required
@user_passes_test(is_admin)
def staff_list_view(request):
    """Danh sách nhân viên (cho Admin)"""
    staff = User.objects.filter(user_type__in=['staff', 'admin']).order_by('-date_joined')

    context = {
        'staff': staff,
        'page_title': 'Danh sách nhân viên',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Nhân viên', 'url': None}
        ]
    }
    return render(request, 'accounts/staff_list.html', context)


@login_required
@user_passes_test(is_admin)
def staff_detail_view(request, user_id):
    """Chi tiết thông tin nhân viên (cho Admin)"""
    staff = get_object_or_404(User, pk=user_id, user_type__in=['staff', 'admin'])

    try:
        profile = staff.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=staff)

    context = {
        'staff': staff,
        'profile': profile,
        'page_title': f'Thông tin nhân viên: {staff.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Nhân viên', 'url': reverse_lazy('accounts:staff_list')},
            {'title': staff.full_name, 'url': None}
        ]
    }
    return render(request, 'accounts/staff_detail.html', context)


@login_required
@user_passes_test(is_admin)
def staff_edit_view(request, user_id):
    """Chỉnh sửa thông tin nhân viên (cho Admin)"""
    staff = get_object_or_404(User, pk=user_id, user_type__in=['staff', 'admin'])

    try:
        profile = staff.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=staff)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=staff)
        profile_form = UserProfileExtendedForm(request.POST, instance=profile)

        if form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                form.save()
                profile_form.save()

            messages.success(request, f'Thông tin nhân viên {staff.full_name} đã được cập nhật thành công.')
            return redirect('accounts:staff_detail', user_id=staff.id)
    else:
        form = AdminUserEditForm(instance=staff)
        profile_form = UserProfileExtendedForm(instance=profile)

    context = {
        'form': form,
        'profile_form': profile_form,
        'staff': staff,
        'page_title': f'Chỉnh sửa nhân viên: {staff.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Nhân viên', 'url': reverse_lazy('accounts:staff_list')},
            {'title': staff.full_name, 'url': reverse_lazy('accounts:staff_detail', kwargs={'user_id': staff.id})},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'accounts/staff_edit.html', context)


@login_required
@user_passes_test(is_admin)
def staff_delete_view(request, user_id):
    """Xóa nhân viên (cho Admin)"""
    staff = get_object_or_404(User, pk=user_id, user_type__in=['staff', 'admin'])

    if staff.id == request.user.id:
        messages.error(request, 'Bạn không thể xóa tài khoản của chính mình.')
        return redirect('accounts:staff_list')

    if request.method == 'POST':
        staff_name = staff.full_name
        staff.delete()
        messages.success(request, f'Nhân viên {staff_name} đã được xóa thành công.')
        return redirect('accounts:staff_list')

    context = {
        'staff': staff,
        'page_title': f'Xóa nhân viên: {staff.full_name}',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Nhân viên', 'url': reverse_lazy('accounts:staff_list')},
            {'title': staff.full_name, 'url': reverse_lazy('accounts:staff_detail', kwargs={'user_id': staff.id})},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'accounts/staff_delete.html', context)


@login_required
@user_passes_test(is_admin)
def user_create_view(request):
    """Tạo tài khoản người dùng mới (cho Admin)"""
    if request.method == 'POST':
        form = AdminUserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()

            UserProfile.objects.create(user=user)

            messages.success(request, f'Tài khoản {user.full_name} đã được tạo thành công.')

            if user.user_type == 'student':
                return redirect('accounts:student_detail', user_id=user.id)
            else:
                return redirect('accounts:staff_detail', user_id=user.id)
    else:
        form = AdminUserCreateForm()

    context = {
        'form': form,
        'page_title': 'Tạo tài khoản mới',
        'breadcrumbs': [
            {'title': 'Quản lý người dùng', 'url': '#'},
            {'title': 'Tạo tài khoản', 'url': None}
        ]
    }
    return render(request, 'accounts/user_create.html', context)