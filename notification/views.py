from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from accounts.models import User
from dormitory.models import Building, Room
from .models import NotificationCategory, Notification, UserNotification, Announcement
from .forms import NotificationCategoryForm, NotificationForm, AnnouncementForm


def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'

def is_admin_or_staff(user):
    return user.is_authenticated and user.user_type in ['admin', 'staff']


# ====== Views cho người dùng ======

@login_required
def notification_list_view(request):
    """Danh sách thông báo của người dùng"""
    user_notifications = UserNotification.objects.filter(
        user=request.user
    ).select_related('notification', 'notification__category').order_by('-created_at')

    context = {
        'user_notifications': user_notifications,
        'page_title': 'Thông báo của tôi',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': None}
        ]
    }
    return render(request, 'notification/notification_list.html', context)


@login_required
def notification_detail_view(request, notification_id):
    """Chi tiết thông báo"""
    notification = get_object_or_404(Notification, id=notification_id)

    try:
        user_notification = UserNotification.objects.get(
            user=request.user,
            notification=notification
        )
    except UserNotification.DoesNotExist:
        if not (notification.is_global or is_admin_or_staff(request.user)):
            messages.error(request, 'Bạn không có quyền xem thông báo này.')
            return redirect('notification:list')
        user_notification = None

    if user_notification and not user_notification.is_read:
        user_notification.mark_as_read()

    context = {
        'notification': notification,
        'user_notification': user_notification,
        'page_title': notification.title,
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': reverse('notification:list')},
            {'title': notification.title, 'url': None}
        ]
    }
    return render(request, 'notification/notification_detail.html', context)


@login_required
def mark_as_read_view(request, notification_id):
    """Đánh dấu thông báo là đã đọc"""
    user_notification = get_object_or_404(
        UserNotification,
        notification_id=notification_id,
        user=request.user
    )

    user_notification.mark_as_read()
    next_url = request.GET.get('next', 'notification:list')
    if next_url == 'detail':
        return redirect('notification:detail', notification_id=notification_id)

    return redirect('notification:list')


@login_required
def mark_all_as_read_view(request):
    """Đánh dấu tất cả thông báo là đã đọc"""
    UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True, read_at=timezone.now())

    messages.success(request, 'Đã đánh dấu tất cả thông báo là đã đọc.')
    return redirect('notification:list')


@login_required
def announcement_list_view(request):
    """Danh sách thông báo chung"""
    now = timezone.now()
    announcements = Announcement.objects.filter(
        is_active=True,
        start_date__lte=now
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=now)
    ).order_by('-is_pinned', '-created_at')

    context = {
        'announcements': announcements,
        'page_title': 'Thông báo chung',
        'breadcrumbs': [
            {'title': 'Thông báo chung', 'url': None}
        ]
    }
    return render(request, 'notification/announcement_list.html', context)


@login_required
def announcement_detail_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)

    context = {
        'announcement': announcement,
        'page_title': announcement.title,
        'breadcrumbs': [
            {'title': 'Thông báo chung', 'url': reverse('notification:announcement_list')},
            {'title': announcement.title, 'url': None}
        ]
    }
    return render(request, 'notification/announcement_detail.html', context)


# ====== Views cho Admin ======

@login_required
@user_passes_test(is_admin_or_staff)
def category_list_view(request):
    """Danh sách danh mục thông báo"""
    categories = NotificationCategory.objects.all().order_by('name')

    context = {
        'categories': categories,
        'page_title': 'Danh mục thông báo',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh mục', 'url': None}
        ]
    }
    return render(request, 'notification/category_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_create_view(request):
    """Tạo danh mục thông báo mới"""
    if request.method == 'POST':
        form = NotificationCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo danh mục thông báo mới thành công.')
            return redirect('notification:category_list')
    else:
        form = NotificationCategoryForm()

    context = {
        'form': form,
        'page_title': 'Tạo danh mục thông báo',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('notification:category_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'notification/category_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_edit_view(request, category_id):
    """Chỉnh sửa danh mục thông báo"""
    category = get_object_or_404(NotificationCategory, id=category_id)

    if request.method == 'POST':
        form = NotificationCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật danh mục thông báo thành công.')
            return redirect('notification:category_list')
    else:
        form = NotificationCategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'page_title': f'Chỉnh sửa danh mục: {category.name}',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('notification:category_list')},
            {'title': category.name, 'url': None}
        ]
    }
    return render(request, 'notification/category_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_delete_view(request, category_id):
    """Xóa danh mục thông báo"""
    category = get_object_or_404(NotificationCategory, id=category_id)

    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Đã xóa danh mục: {category_name}')
        return redirect('notification:category_list')

    context = {
        'category': category,
        'page_title': f'Xóa danh mục: {category.name}',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('notification:category_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'notification/category_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def notification_create_view(request):
    """Tạo thông báo mới"""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                notification = form.save(commit=False)
                notification.sender = request.user
                notification.save()

                if 'target_buildings' in form.cleaned_data:
                    notification.target_buildings.set(form.cleaned_data['target_buildings'])
                if 'target_rooms' in form.cleaned_data:
                    notification.target_rooms.set(form.cleaned_data['target_rooms'])

                user_target = form.cleaned_data.get('user_target')

                recipients = []

                if user_target == 'all':
                    recipients = User.objects.filter(is_active=True)
                elif user_target == 'students':
                    recipients = User.objects.filter(is_active=True, user_type='student')
                elif user_target == 'staff':
                    recipients = User.objects.filter(is_active=True, user_type__in=['staff', 'admin'])
                elif user_target == 'building':
                    buildings = form.cleaned_data.get('target_buildings')
                    if buildings:
                        rooms = Room.objects.filter(building__in=buildings)
                        from registration.models import Contract
                        contracts = Contract.objects.filter(
                            room__in=rooms,
                            status='active',
                            start_date__lte=timezone.now().date(),
                            end_date__gte=timezone.now().date()
                        )
                        recipients = [contract.user for contract in contracts]
                elif user_target == 'room':
                    rooms = form.cleaned_data.get('target_rooms')
                    if rooms:
                        from registration.models import Contract
                        contracts = Contract.objects.filter(
                            room__in=rooms,
                            status='active',
                            start_date__lte=timezone.now().date(),
                            end_date__gte=timezone.now().date()
                        )
                        recipients = [contract.user for contract in contracts]
                elif user_target == 'specific':
                    specific_users = form.cleaned_data.get('specific_users')
                    if specific_users:
                        recipients = specific_users

                for user in recipients:
                    UserNotification.objects.create(
                        notification=notification,
                        user=user
                    )

            messages.success(request, 'Tạo thông báo mới thành công.')
            return redirect('notification:list')
    else:
        form = NotificationForm()

    context = {
        'form': form,
        'page_title': 'Tạo thông báo mới',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'notification/notification_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def notification_edit_view(request, notification_id):
    """Chỉnh sửa thông báo"""
    notification = get_object_or_404(Notification, id=notification_id)

    if request.method == 'POST':
        form = NotificationForm(request.POST, instance=notification)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thông báo thành công.')
            return redirect('notification:list')
    else:
        form = NotificationForm(instance=notification)

    context = {
        'form': form,
        'notification': notification,
        'page_title': f'Chỉnh sửa thông báo: {notification.title}',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh sách', 'url': reverse('notification:list')},
            {'title': notification.title, 'url': None}
        ]
    }
    return render(request, 'notification/notification_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def notification_delete_view(request, notification_id):
    """Xóa thông báo"""
    notification = get_object_or_404(Notification, id=notification_id)

    if request.method == 'POST':
        notification_title = notification.title
        notification.delete()
        messages.success(request, f'Đã xóa thông báo: {notification_title}')
        return redirect('notification:list')

    context = {
        'notification': notification,
        'page_title': f'Xóa thông báo: {notification.title}',
        'breadcrumbs': [
            {'title': 'Thông báo', 'url': '#'},
            {'title': 'Danh sách', 'url': reverse('notification:list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'notification/notification_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def announcement_create_view(request):
    """Tạo thông báo chung"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.save()
            messages.success(request, 'Tạo thông báo chung mới thành công.')
            return redirect('notification:announcement_list')
    else:
        form = AnnouncementForm()

    context = {
        'form': form,
        'page_title': 'Tạo thông báo chung mới',
        'breadcrumbs': [
            {'title': 'Thông báo chung', 'url': reverse('notification:announcement_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'notification/announcement_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def announcement_edit_view(request, announcement_id):
    """Chỉnh sửa thông báo chung"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, request.FILES, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật thông báo chung thành công.')
            return redirect('notification:announcement_list')
    else:
        form = AnnouncementForm(instance=announcement)

    context = {
        'form': form,
        'announcement': announcement,
        'page_title': f'Chỉnh sửa thông báo chung: {announcement.title}',
        'breadcrumbs': [
            {'title': 'Thông báo chung', 'url': reverse('notification:announcement_list')},
            {'title': announcement.title, 'url': reverse('notification:announcement_detail', args=[announcement.id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'notification/announcement_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def announcement_delete_view(request, announcement_id):
    """Xóa thông báo chung"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    if request.method == 'POST':
        announcement_title = announcement.title
        announcement.delete()
        messages.success(request, f'Đã xóa thông báo chung: {announcement_title}')
        return redirect('notification:announcement_list')

    context = {
        'announcement': announcement,
        'page_title': f'Xóa thông báo chung: {announcement.title}',
        'breadcrumbs': [
            {'title': 'Thông báo chung', 'url': reverse('notification:announcement_list')},
            {'title': announcement.title, 'url': reverse('notification:announcement_detail', args=[announcement.id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'notification/announcement_delete.html', context)


@login_required
def unread_count_api(request):
    """API trả về số lượng thông báo chưa đọc"""
    count = UserNotification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})