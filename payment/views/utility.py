from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.urls import reverse
import datetime

from accounts.views import is_admin_or_staff
from dormitory.models import Room
from payment.models import ElectricityReading, WaterReading
from payment.forms import ElectricityReadingForm, WaterReadingForm


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_reading_list_view(request):
    """Danh sách chỉ số điện"""
    readings = ElectricityReading.objects.all().select_related('room', 'room__building')
    
    # Lọc theo phòng
    room_id = request.GET.get('room')
    if room_id:
        readings = readings.filter(room_id=room_id)
    
    # Lọc theo tháng/năm
    month = request.GET.get('month')
    year = request.GET.get('year')
    if month and year:
        readings = readings.filter(month=month, year=year)
    
    # Lọc theo trạng thái hóa đơn
    is_billed = request.GET.get('is_billed')
    if is_billed is not None:
        is_billed = is_billed.lower() == 'true'
        readings = readings.filter(is_billed=is_billed)
    
    # Tìm kiếm
    search_query = request.GET.get('q')
    if search_query:
        readings = readings.filter(
            Q(room__room_number__icontains=search_query) |
            Q(room__building__name__icontains=search_query)
        )
    
    # Sắp xếp
    readings = readings.order_by('-year', '-month', 'room__building__name', 'room__room_number')
    
    # Phân trang
    paginator = Paginator(readings, 10)
    page_number = request.GET.get('page', 1)
    readings_page = paginator.get_page(page_number)
    
    context = {
        'readings': readings_page,
        'rooms': Room.objects.filter(is_active=True),
        'month': month,
        'year': year,
        'is_billed': is_billed,
        'search_query': search_query,
        'page_title': 'Danh sách chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': None}
        ]
    }
    
    return render(request, 'payment/electricity_reading_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_reading_create_view(request):
    """Tạo chỉ số điện mới"""
    if request.method == 'POST':
        form = ElectricityReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            
            # Kiểm tra xem đã có chỉ số cho tháng này chưa
            existing_reading = ElectricityReading.objects.filter(
                room=reading.room,
                month=reading.month,
                year=reading.year
            ).first()
            
            if existing_reading:
                messages.error(request, f'Đã có chỉ số điện cho phòng {reading.room} tháng {reading.month}/{reading.year}.')
                return redirect('payment:electricity_reading_list')
            
            # Lấy chỉ số tháng trước
            previous_month = reading.month - 1
            previous_year = reading.year
            if previous_month == 0:
                previous_month = 12
                previous_year -= 1
            
            previous_reading = ElectricityReading.objects.filter(
                room=reading.room,
                month=previous_month,
                year=previous_year
            ).first()
            
            if previous_reading:
                reading.previous_reading = previous_reading.current_reading
            else:
                reading.previous_reading = 0
            
            reading.save()
            
            messages.success(request, 'Đã tạo chỉ số điện mới thành công.')
            return redirect('payment:electricity_reading_list')
    else:
        form = ElectricityReadingForm(initial={
            'reading_date': timezone.now().date(),
            'month': timezone.now().month,
            'year': timezone.now().year
        })
    
    context = {
        'form': form,
        'page_title': 'Tạo chỉ số điện mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_reading_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    
    return render(request, 'payment/electricity_reading_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_reading_edit_view(request, reading_id):
    """Chỉnh sửa chỉ số điện"""
    reading = get_object_or_404(ElectricityReading, pk=reading_id)
    
    if reading.is_billed:
        messages.error(request, 'Không thể chỉnh sửa chỉ số điện đã lập hóa đơn.')
        return redirect('payment:electricity_reading_list')
    
    if request.method == 'POST':
        form = ElectricityReadingForm(request.POST, instance=reading)
        if form.is_valid():
            form.save()
            
            messages.success(request, 'Đã cập nhật chỉ số điện thành công.')
            return redirect('payment:electricity_reading_list')
    else:
        form = ElectricityReadingForm(instance=reading)
    
    context = {
        'form': form,
        'reading': reading,
        'page_title': f'Chỉnh sửa chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_reading_list')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    
    return render(request, 'payment/electricity_reading_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_reading_delete_view(request, reading_id):
    """Xóa chỉ số điện"""
    reading = get_object_or_404(ElectricityReading, pk=reading_id)
    
    if reading.is_billed:
        messages.error(request, 'Không thể xóa chỉ số điện đã lập hóa đơn.')
        return redirect('payment:electricity_reading_list')
    
    if request.method == 'POST':
        reading.delete()
        
        messages.success(request, 'Đã xóa chỉ số điện thành công.')
        return redirect('payment:electricity_reading_list')
    
    context = {
        'reading': reading,
        'page_title': f'Xóa chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_reading_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    
    return render(request, 'payment/electricity_reading_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_reading_list_view(request):
    """Danh sách chỉ số nước"""
    readings = WaterReading.objects.all().select_related('room', 'room__building')
    
    # Lọc theo phòng
    room_id = request.GET.get('room')
    if room_id:
        readings = readings.filter(room_id=room_id)
    
    # Lọc theo tháng/năm
    month = request.GET.get('month')
    year = request.GET.get('year')
    if month and year:
        readings = readings.filter(month=month, year=year)
    
    # Lọc theo trạng thái hóa đơn
    is_billed = request.GET.get('is_billed')
    if is_billed is not None:
        is_billed = is_billed.lower() == 'true'
        readings = readings.filter(is_billed=is_billed)
    
    # Tìm kiếm
    search_query = request.GET.get('q')
    if search_query:
        readings = readings.filter(
            Q(room__room_number__icontains=search_query) |
            Q(room__building__name__icontains=search_query)
        )
    
    # Sắp xếp
    readings = readings.order_by('-year', '-month', 'room__building__name', 'room__room_number')
    
    # Phân trang
    paginator = Paginator(readings, 10)
    page_number = request.GET.get('page', 1)
    readings_page = paginator.get_page(page_number)
    
    context = {
        'readings': readings_page,
        'rooms': Room.objects.filter(is_active=True),
        'month': month,
        'year': year,
        'is_billed': is_billed,
        'search_query': search_query,
        'page_title': 'Danh sách chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': None}
        ]
    }
    
    return render(request, 'payment/water_reading_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_reading_create_view(request):
    """Tạo chỉ số nước mới"""
    if request.method == 'POST':
        form = WaterReadingForm(request.POST)
        if form.is_valid():
            reading = form.save(commit=False)
            
            # Kiểm tra xem đã có chỉ số cho tháng này chưa
            existing_reading = WaterReading.objects.filter(
                room=reading.room,
                month=reading.month,
                year=reading.year
            ).first()
            
            if existing_reading:
                messages.error(request, f'Đã có chỉ số nước cho phòng {reading.room} tháng {reading.month}/{reading.year}.')
                return redirect('payment:water_reading_list')
            
            # Lấy chỉ số tháng trước
            previous_month = reading.month - 1
            previous_year = reading.year
            if previous_month == 0:
                previous_month = 12
                previous_year -= 1
            
            previous_reading = WaterReading.objects.filter(
                room=reading.room,
                month=previous_month,
                year=previous_year
            ).first()
            
            if previous_reading:
                reading.previous_reading = previous_reading.current_reading
            else:
                reading.previous_reading = 0
            
            reading.save()
            
            messages.success(request, 'Đã tạo chỉ số nước mới thành công.')
            return redirect('payment:water_reading_list')
    else:
        form = WaterReadingForm(initial={
            'reading_date': timezone.now().date(),
            'month': timezone.now().month,
            'year': timezone.now().year
        })
    
    context = {
        'form': form,
        'page_title': 'Tạo chỉ số nước mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_reading_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    
    return render(request, 'payment/water_reading_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_reading_edit_view(request, reading_id):
    """Chỉnh sửa chỉ số nước"""
    reading = get_object_or_404(WaterReading, pk=reading_id)
    
    if reading.is_billed:
        messages.error(request, 'Không thể chỉnh sửa chỉ số nước đã lập hóa đơn.')
        return redirect('payment:water_reading_list')
    
    if request.method == 'POST':
        form = WaterReadingForm(request.POST, instance=reading)
        if form.is_valid():
            form.save()
            
            messages.success(request, 'Đã cập nhật chỉ số nước thành công.')
            return redirect('payment:water_reading_list')
    else:
        form = WaterReadingForm(instance=reading)
    
    context = {
        'form': form,
        'reading': reading,
        'page_title': f'Chỉnh sửa chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_reading_list')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    
    return render(request, 'payment/water_reading_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_reading_delete_view(request, reading_id):
    """Xóa chỉ số nước"""
    reading = get_object_or_404(WaterReading, pk=reading_id)
    
    if reading.is_billed:
        messages.error(request, 'Không thể xóa chỉ số nước đã lập hóa đơn.')
        return redirect('payment:water_reading_list')
    
    if request.method == 'POST':
        reading.delete()
        
        messages.success(request, 'Đã xóa chỉ số nước thành công.')
        return redirect('payment:water_reading_list')
    
    context = {
        'reading': reading,
        'page_title': f'Xóa chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_reading_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    
    return render(request, 'payment/water_reading_delete.html', context)
