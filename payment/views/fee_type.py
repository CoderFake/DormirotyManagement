from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q
from django.core.paginator import Paginator

from accounts.views import is_admin_or_staff
from payment.models import FeeType
from payment.forms import FeeTypeForm


@login_required
@user_passes_test(is_admin_or_staff)
def fee_type_list_view(request):
    """Danh sách loại phí"""
    fee_types = FeeType.objects.all()

    # Tìm kiếm
    search_query = request.GET.get('q')
    if search_query:
        fee_types = fee_types.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    # Lọc theo trạng thái
    is_active = request.GET.get('is_active')
    if is_active is not None:
        is_active = is_active.lower() == 'true'
        fee_types = fee_types.filter(is_active=is_active)

    # Lọc theo loại phí định kỳ
    is_recurring = request.GET.get('is_recurring')
    if is_recurring is not None:
        is_recurring = is_recurring.lower() == 'true'
        fee_types = fee_types.filter(is_recurring=is_recurring)

    # Sắp xếp
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'name':
        fee_types = fee_types.order_by('name')
    elif sort_by == 'code':
        fee_types = fee_types.order_by('code')
    elif sort_by == '-created_at':
        fee_types = fee_types.order_by('-created_at')

    # Phân trang
    paginator = Paginator(fee_types, 10)
    page_number = request.GET.get('page', 1)
    fee_types_page = paginator.get_page(page_number)

    context = {
        'fee_types': fee_types_page,
        'search_query': search_query,
        'is_active': is_active,
        'is_recurring': is_recurring,
        'sort_by': sort_by,
        'page_title': 'Danh sách loại phí',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Loại phí', 'url': None}
        ]
    }

    return render(request, 'payment/fee_type_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def fee_type_create_view(request):
    """Tạo loại phí mới"""
    if request.method == 'POST':
        form = FeeTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã tạo loại phí mới thành công.')
            return redirect('payment:fee_type_list')
    else:
        form = FeeTypeForm()

    context = {
        'form': form,
        'page_title': 'Tạo loại phí mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Loại phí', 'url': reverse('payment:fee_type_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }

    return render(request, 'payment/fee_type_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def fee_type_edit_view(request, fee_type_id):
    """Chỉnh sửa loại phí"""
    fee_type = get_object_or_404(FeeType, pk=fee_type_id)

    if request.method == 'POST':
        form = FeeTypeForm(request.POST, instance=fee_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật loại phí thành công.')
            return redirect('payment:fee_type_list')
    else:
        form = FeeTypeForm(instance=fee_type)

    context = {
        'form': form,
        'fee_type': fee_type,
        'page_title': f'Chỉnh sửa loại phí: {fee_type.name}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Loại phí', 'url': reverse('payment:fee_type_list')},
            {'title': fee_type.name, 'url': None}
        ]
    }

    return render(request, 'payment/fee_type_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def fee_type_delete_view(request, fee_type_id):
    """Xóa loại phí"""
    fee_type = get_object_or_404(FeeType, pk=fee_type_id)

    if request.method == 'POST':
        fee_type_name = fee_type.name
        fee_type.delete()
        messages.success(request, f'Đã xóa loại phí: {fee_type_name}')
        return redirect('payment:fee_type_list')

    context = {
        'fee_type': fee_type,
        'page_title': f'Xóa loại phí: {fee_type.name}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Loại phí', 'url': reverse('payment:fee_type_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }

    return render(request, 'payment/fee_type_delete.html', context)