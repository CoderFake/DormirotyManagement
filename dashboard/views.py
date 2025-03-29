from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from accounts.models import User
from dormitory.models import Building, Room, RoomType
from registration.models import Contract, RoomRegistration, RegistrationPeriod
from payment.models import Invoice, Payment
from maintenance.models import MaintenanceRequest
from notification.models import Notification, UserNotification


@login_required
def index(request):
    """Dashboard chính"""

    if request.user.user_type in ['admin', 'staff']:
        return admin_dashboard(request)
    else:
        return student_dashboard(request)


def student_dashboard(request):
    """Dashboard cho sinh viên"""

    current_contract = Contract.objects.filter(
        user=request.user,
        status='active',
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).first()

    current_registration = None
    if not current_contract:
        current_registration = RoomRegistration.objects.filter(
            user=request.user,
            status__in=['pending', 'approved']
        ).order_by('-registration_date').first()

    unpaid_invoices = Invoice.objects.filter(
        user=request.user,
        status__in=['pending', 'overdue', 'partially_paid']
    ).order_by('due_date')

    total_due_amount = sum(invoice.get_remaining_amount() for invoice in unpaid_invoices)

    maintenance_requests = MaintenanceRequest.objects.filter(
        user=request.user
    ).order_by('-requested_date')[:5]

    unread_notifications = UserNotification.objects.filter(
        user=request.user,
        is_read=False
    ).order_by('-created_at')[:5]

    active_periods = RegistrationPeriod.objects.filter(
        status='active',
        is_active=True
    )

    context = {
        'current_contract': current_contract,
        'current_registration': current_registration,
        'unpaid_invoices': unpaid_invoices,
        'total_due_amount': total_due_amount,
        'maintenance_requests': maintenance_requests,
        'unread_notifications': unread_notifications,
        'active_periods': active_periods,
        'page_title': 'Dashboard',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': None}
        ]
    }

    return render(request, 'dashboard/student_dashboard.html', context)


def admin_dashboard(request):
    """Dashboard cho quản trị viên và nhân viên"""

    total_students = User.objects.filter(user_type='student').count()
    total_rooms = Room.objects.count()
    available_rooms = Room.objects.filter(status__in=['available', 'partially_occupied']).count()
    occupied_rooms = Room.objects.filter(status='fully_occupied').count()

    current_year = timezone.now().year
    monthly_revenue = []
    for month in range(1, 13):
        revenue = Payment.objects.filter(
            payment_date__year=current_year,
            payment_date__month=month,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_revenue.append({
            'month': month,
            'revenue': revenue
        })

    new_maintenance_requests = MaintenanceRequest.objects.filter(
        status='pending'
    ).order_by('-requested_date')[:5]

    new_registrations = RoomRegistration.objects.filter(
        status='pending'
    ).order_by('-registration_date')[:5]

    buildings = Building.objects.annotate(
        total_rooms=Count('rooms'),
        occupied_rooms=Count('rooms', filter=Q(
            rooms__status='fully_occupied'
        ))
    )

    pending_invoices = Invoice.objects.filter(status='pending').count()
    overdue_invoices = Invoice.objects.filter(status='overdue').count()

    context = {
        'total_students': total_students,
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'monthly_revenue': monthly_revenue,
        'new_maintenance_requests': new_maintenance_requests,
        'new_registrations': new_registrations,
        'buildings': buildings,
        'pending_invoices': pending_invoices,
        'overdue_invoices': overdue_invoices,
        'page_title': 'Dashboard Quản trị',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': None}
        ]
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def system_settings(request):
    """Trang cài đặt hệ thống"""

    if request.user.user_type != 'admin':
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        messages.success(request, 'Đã lưu cài đặt hệ thống.')
        return redirect('dashboard:system_settings')

    context = {
        'page_title': 'Cài đặt Hệ thống',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/dashboard/'},
            {'title': 'Cài đặt Hệ thống', 'url': None}
        ]
    }

    return render(request, 'dashboard/system_settings.html', context)


@login_required
def occupancy_report(request):
    """Báo cáo lưu trú"""

    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('dashboard:index')

    building_id = request.GET.get('building')
    if building_id:
        rooms = Room.objects.filter(building_id=building_id)
    else:
        rooms = Room.objects.all()

    status_stats = rooms.values('status').annotate(count=Count('id'))

    room_type_stats = rooms.values('room_type__name').annotate(count=Count('id'))

    buildings = Building.objects.all()

    context = {
        'status_stats': status_stats,
        'room_type_stats': room_type_stats,
        'buildings': buildings,
        'selected_building': building_id,
        'page_title': 'Báo cáo Lưu trú',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/dashboard/'},
            {'title': 'Báo cáo Lưu trú', 'url': None}
        ]
    }

    return render(request, 'dashboard/occupancy_report.html', context)


@login_required
def revenue_report(request):
    """Báo cáo doanh thu"""

    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('dashboard:index')

    year = request.GET.get('year', str(timezone.now().year))

    monthly_revenue = []
    for month in range(1, 13):
        revenue = Payment.objects.filter(
            payment_date__year=int(year),
            payment_date__month=month,
            status='completed'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly_revenue.append({
            'month': month,
            'revenue': revenue
        })

    fee_type_revenue = Payment.objects.filter(
        payment_date__year=int(year),
        status='completed'
    ).values(
        'invoice__items__fee_type__name'
    ).annotate(
        total=Sum('amount')
    ).order_by('-total')

    context = {
        'monthly_revenue': monthly_revenue,
        'fee_type_revenue': fee_type_revenue,
        'year': year,
        'available_years': range(2020, timezone.now().year + 1),
        'page_title': 'Báo cáo Doanh thu',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/dashboard/'},
            {'title': 'Báo cáo Doanh thu', 'url': None}
        ]
    }

    return render(request, 'dashboard/revenue_report.html', context)


@login_required
def maintenance_report(request):
    """Báo cáo bảo trì"""

    if request.user.user_type not in ['admin', 'staff']:
        messages.error(request, 'Bạn không có quyền truy cập trang này.')
        return redirect('dashboard:index')

    period = request.GET.get('period', 'month')

    start_date = None
    if period == 'week':
        start_date = timezone.now().date() - timezone.timedelta(days=7)
    elif period == 'month':
        start_date = timezone.now().date() - timezone.timedelta(days=30)
    elif period == 'quarter':
        start_date = timezone.now().date() - timezone.timedelta(days=90)
    elif period == 'year':
        start_date = timezone.now().date() - timezone.timedelta(days=365)

    # Yêu cầu bảo trì theo trạng thái
    status_stats = MaintenanceRequest.objects.filter(
        requested_date__date__gte=start_date
    ).values('status').annotate(count=Count('id'))

    # Yêu cầu bảo trì theo danh mục
    category_stats = MaintenanceRequest.objects.filter(
        requested_date__date__gte=start_date
    ).values('category__name').annotate(count=Count('id'))

    # Yêu cầu bảo trì theo tòa nhà
    building_stats = MaintenanceRequest.objects.filter(
        requested_date__date__gte=start_date
    ).values('building__name').annotate(count=Count('id'))

    context = {
        'status_stats': status_stats,
        'category_stats': category_stats,
        'building_stats': building_stats,
        'period': period,
        'page_title': 'Báo cáo Bảo trì',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/dashboard/'},
            {'title': 'Báo cáo Bảo trì', 'url': None}
        ]
    }

    return render(request, 'dashboard/maintenance_report.html', context)


@login_required
def notification_settings(request):
    """Cài đặt thông báo"""

    if request.method == 'POST':
        messages.success(request, 'Đã lưu cài đặt thông báo.')
        return redirect('dashboard:notification_settings')

    context = {
        'page_title': 'Cài đặt Thông báo',
        'breadcrumbs': [
            {'title': 'Dashboard', 'url': '/dashboard/'},
            {'title': 'Cài đặt Thông báo', 'url': None}
        ]
    }

    return render(request, 'dashboard/notification_settings.html', context)
