from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from dormitory.models import Building
from registration.models import Contract
from .models import MaintenanceCategory, MaintenanceRequest, MaintenanceComment, MaintenanceImage
from .forms import (
    MaintenanceCategoryForm, MaintenanceRequestForm, MaintenanceCommentForm,
    MaintenanceRequestAdminForm, MaintenanceAssignForm
)


def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'


def is_admin_or_staff(user):
    return user.is_authenticated and user.user_type in ['admin', 'staff']


# === Views cho sinh viên ===

@login_required
def request_create_view(request):
    """Tạo yêu cầu bảo trì mới"""
    current_contract = Contract.objects.filter(
        user=request.user,
        status='active',
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).first()

    if not current_contract:
        messages.error(request, 'Bạn không có phòng ở hiện tại. Vui lòng đăng ký phòng trước khi tạo yêu cầu bảo trì.')
        return redirect('dashboard:index')

    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES)
        if form.is_valid():
            maintenance_request = form.save(commit=False)
            maintenance_request.user = request.user
            maintenance_request.room = current_contract.room
            maintenance_request.building = current_contract.room.building
            maintenance_request.save()

            files = request.FILES.getlist('images')
            for f in files:
                MaintenanceImage.objects.create(
                    maintenance_request=maintenance_request,
                    image=f,
                    uploaded_by=request.user
                )

            messages.success(request, 'Yêu cầu bảo trì đã được gửi thành công.')
            return redirect('maintenance:my_requests')
    else:
        form = MaintenanceRequestForm()
        form.fields['room'].initial = current_contract.room

    context = {
        'form': form,
        'contract': current_contract,
        'page_title': 'Tạo yêu cầu bảo trì mới',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Tạo yêu cầu mới', 'url': None}
        ]
    }
    return render(request, 'maintenance/request_form.html', context)


@login_required
def my_requests_view(request):
    """Xem danh sách yêu cầu bảo trì của người dùng"""
    requests = MaintenanceRequest.objects.filter(user=request.user).order_by('-requested_date')

    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)

    context = {
        'requests': requests,
        'page_title': 'Yêu cầu bảo trì của tôi',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Yêu cầu của tôi', 'url': None}
        ]
    }
    return render(request, 'maintenance/my_requests.html', context)


@login_required
def request_detail_view(request, request_id):
    """Xem chi tiết yêu cầu bảo trì"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    # Kiểm tra quyền truy cập
    if not (maintenance_request.user == request.user or is_admin_or_staff(request.user)):
        messages.error(request, 'Bạn không có quyền xem yêu cầu này.')
        return redirect('maintenance:my_requests')

    if request.method == 'POST':
        comment_form = MaintenanceCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.maintenance_request = maintenance_request
            comment.user = request.user
            comment.save()
            messages.success(request, 'Bình luận đã được thêm.')
            return redirect('maintenance:request_detail', request_id=request_id)
    else:
        comment_form = MaintenanceCommentForm()

    comments = MaintenanceComment.objects.filter(maintenance_request=maintenance_request).order_by('created_at')
    images = MaintenanceImage.objects.filter(maintenance_request=maintenance_request).order_by('-created_at')

    context = {
        'maintenance_request': maintenance_request,
        'comments': comments,
        'images': images,
        'comment_form': comment_form,
        'page_title': f'Chi tiết yêu cầu #{maintenance_request.request_number}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Yêu cầu của tôi', 'url': reverse('maintenance:my_requests')},
            {'title': f'#{maintenance_request.request_number}', 'url': None}
        ]
    }
    return render(request, 'maintenance/request_detail.html', context)


@login_required
def request_update_view(request, request_id):
    """Cập nhật yêu cầu bảo trì"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    if maintenance_request.user != request.user:
        messages.error(request, 'Bạn không có quyền chỉnh sửa yêu cầu này.')
        return redirect('maintenance:my_requests')

    if maintenance_request.status not in ['pending', 'rejected']:
        messages.error(request, 'Chỉ có thể chỉnh sửa yêu cầu đang chờ xử lý hoặc đã bị từ chối.')
        return redirect('maintenance:request_detail', request_id=request_id)

    if request.method == 'POST':
        form = MaintenanceRequestForm(request.POST, request.FILES, instance=maintenance_request)
        if form.is_valid():
            form.save()

            files = request.FILES.getlist('images')
            for f in files:
                MaintenanceImage.objects.create(
                    maintenance_request=maintenance_request,
                    image=f,
                    uploaded_by=request.user
                )

            messages.success(request, 'Yêu cầu bảo trì đã được cập nhật.')
            return redirect('maintenance:request_detail', request_id=request_id)
    else:
        form = MaintenanceRequestForm(instance=maintenance_request)

    context = {
        'form': form,
        'maintenance_request': maintenance_request,
        'page_title': f'Cập nhật yêu cầu #{maintenance_request.request_number}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Yêu cầu của tôi', 'url': reverse('maintenance:my_requests')},
            {'title': f'#{maintenance_request.request_number}',
             'url': reverse('maintenance:request_detail', args=[request_id])},
            {'title': 'Cập nhật', 'url': None}
        ]
    }
    return render(request, 'maintenance/request_form.html', context)


@login_required
def request_cancel_view(request, request_id):
    """Hủy yêu cầu bảo trì"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    if maintenance_request.user != request.user:
        messages.error(request, 'Bạn không có quyền hủy yêu cầu này.')
        return redirect('maintenance:my_requests')

    if maintenance_request.status not in ['pending', 'rejected']:
        messages.error(request, 'Chỉ có thể hủy yêu cầu đang chờ xử lý hoặc đã bị từ chối.')
        return redirect('maintenance:request_detail', request_id=request_id)

    if request.method == 'POST':
        maintenance_request.cancel()
        messages.success(request, 'Đã hủy yêu cầu bảo trì.')
        return redirect('maintenance:my_requests')

    context = {
        'maintenance_request': maintenance_request,
        'page_title': f'Hủy yêu cầu #{maintenance_request.request_number}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Yêu cầu của tôi', 'url': reverse('maintenance:my_requests')},
            {'title': f'#{maintenance_request.request_number}',
             'url': reverse('maintenance:request_detail', args=[request_id])},
            {'title': 'Hủy', 'url': None}
        ]
    }
    return render(request, 'maintenance/request_cancel.html', context)


# === Views cho Admin/Staff ===

@login_required
@user_passes_test(is_admin_or_staff)
def category_list_view(request):
    """Danh sách danh mục bảo trì"""
    categories = MaintenanceCategory.objects.all().order_by('name')

    context = {
        'categories': categories,
        'page_title': 'Danh mục bảo trì',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh mục', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/category_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_create_view(request):
    """Tạo danh mục bảo trì mới"""
    if request.method == 'POST':
        form = MaintenanceCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo danh mục bảo trì mới thành công.')
            return redirect('maintenance:category_list')
    else:
        form = MaintenanceCategoryForm()

    context = {
        'form': form,
        'page_title': 'Tạo danh mục bảo trì',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('maintenance:category_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/category_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_edit_view(request, category_id):
    """Chỉnh sửa danh mục bảo trì"""
    category = get_object_or_404(MaintenanceCategory, pk=category_id)

    if request.method == 'POST':
        form = MaintenanceCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật danh mục bảo trì thành công.')
            return redirect('maintenance:category_list')
    else:
        form = MaintenanceCategoryForm(instance=category)

    context = {
        'form': form,
        'category': category,
        'page_title': f'Chỉnh sửa danh mục: {category.name}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('maintenance:category_list')},
            {'title': category.name, 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/category_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def category_delete_view(request, category_id):
    """Xóa danh mục bảo trì"""
    category = get_object_or_404(MaintenanceCategory, pk=category_id)

    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Đã xóa danh mục: {category_name}')
        return redirect('maintenance:category_list')

    context = {
        'category': category,
        'page_title': f'Xóa danh mục: {category.name}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh mục', 'url': reverse('maintenance:category_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/category_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def request_list_view(request):
    """Danh sách tất cả yêu cầu bảo trì"""
    requests = MaintenanceRequest.objects.all().order_by('-requested_date')

    status = request.GET.get('status')
    if status:
        requests = requests.filter(status=status)

    category = request.GET.get('category')
    if category:
        requests = requests.filter(category_id=category)

    building = request.GET.get('building')
    if building:
        requests = requests.filter(building_id=building)

    priority = request.GET.get('priority')
    if priority:
        requests = requests.filter(priority=priority)

    context = {
        'requests': requests,
        'categories': MaintenanceCategory.objects.all(),
        'buildings': Building.objects.all(),
        'page_title': 'Danh sách yêu cầu bảo trì',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh sách yêu cầu', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/request_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def request_assign_view(request, request_id):
    """Phân công xử lý yêu cầu bảo trì"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    if maintenance_request.status not in ['pending', 'rejected']:
        messages.error(request, 'Chỉ có thể phân công yêu cầu đang chờ xử lý hoặc đã bị từ chối.')
        return redirect('maintenance:request_detail', request_id=request_id)

    if request.method == 'POST':
        form = MaintenanceAssignForm(request.POST)
        if form.is_valid():
            staff = form.cleaned_data['assigned_to']
            maintenance_request.assigned_to = staff
            maintenance_request.status = 'assigned'
            maintenance_request.save()

            MaintenanceComment.objects.create(
                maintenance_request=maintenance_request,
                user=request.user,
                comment=f'Yêu cầu đã được phân công cho {staff.full_name}'
            )

            messages.success(request, f'Đã phân công yêu cầu cho {staff.full_name}.')
            return redirect('maintenance:request_detail', request_id=request_id)
    else:
        form = MaintenanceAssignForm()

    context = {
        'form': form,
        'maintenance_request': maintenance_request,
        'page_title': f'Phân công yêu cầu #{maintenance_request.request_number}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh sách yêu cầu', 'url': reverse('maintenance:request_list')},
            {'title': f'#{maintenance_request.request_number}',
             'url': reverse('maintenance:request_detail', args=[request_id])},
            {'title': 'Phân công', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/request_assign.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def request_admin_edit_view(request, request_id):
    """Chỉnh sửa yêu cầu bảo trì (dành cho Admin)"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    if request.method == 'POST':
        form = MaintenanceRequestAdminForm(request.POST, request.FILES, instance=maintenance_request)
        if form.is_valid():
            form.save()

            files = request.FILES.getlist('images')
            for f in files:
                MaintenanceImage.objects.create(
                    maintenance_request=maintenance_request,
                    image=f,
                    uploaded_by=request.user
                )

            messages.success(request, 'Yêu cầu bảo trì đã được cập nhật.')
            return redirect('maintenance:request_detail', request_id=request_id)
    else:
        form = MaintenanceRequestAdminForm(instance=maintenance_request)

    context = {
        'form': form,
        'maintenance_request': maintenance_request,
        'page_title': f'Chỉnh sửa yêu cầu #{maintenance_request.request_number}',
        'breadcrumbs': [
            {'title': 'Bảo trì', 'url': '#'},
            {'title': 'Danh sách yêu cầu', 'url': reverse('maintenance:request_list')},
            {'title': f'#{maintenance_request.request_number}',
             'url': reverse('maintenance:request_detail', args=[request_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'maintenance/admin/request_admin_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def request_status_update_view(request, request_id):
    """Cập nhật trạng thái yêu cầu bảo trì"""
    maintenance_request = get_object_or_404(MaintenanceRequest, pk=request_id)

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes', '')

        if status == 'in_progress':
            maintenance_request.status = 'in_progress'
            message = 'Đã cập nhật trạng thái yêu cầu sang "Đang xử lý".'

        elif status == 'completed':
            maintenance_request.status = 'completed'
            maintenance_request.completed_date = timezone.now()
            message = 'Đã cập nhật trạng thái yêu cầu sang "Hoàn thành".'

        elif status == 'rejected':
            maintenance_request.status = 'rejected'
            maintenance_request.admin_notes = notes
            message = 'Đã cập nhật trạng thái yêu cầu sang "Từ chối".'

        maintenance_request.save()

        if notes:
            MaintenanceComment.objects.create(
                maintenance_request=maintenance_request,
                user=request.user,
                comment=f'Cập nhật trạng thái: {maintenance_request.get_status_display()}. Ghi chú: {notes}'
            )
        else:
            MaintenanceComment.objects.create(
                maintenance_request=maintenance_request,
                user=request.user,
                comment=f'Cập nhật trạng thái: {maintenance_request.get_status_display()}'
            )

        messages.success(request, message)
        return redirect('maintenance:request_detail', request_id=request_id)

    return redirect('maintenance:request_detail', request_id=request_id)


# API
@login_required
def handle_request_api(request):
    """API xử lý yêu cầu bảo trì"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không được hỗ trợ'}, status=405)

    request_id = request.POST.get('request_id')
    action = request.POST.get('action')
    notes = request.POST.get('notes', '')

    if not request_id or not action:
        return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin yêu cầu'}, status=400)

    try:
        maintenance_request = MaintenanceRequest.objects.get(pk=request_id)
    except MaintenanceRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy yêu cầu'}, status=404)

    if not (maintenance_request.user == request.user or is_admin_or_staff(request.user)):
        return JsonResponse({'status': 'error', 'message': 'Không có quyền thực hiện hành động này'}, status=403)

    try:
        if action == 'cancel':
            if maintenance_request.user != request.user:
                return JsonResponse({'status': 'error', 'message': 'Chỉ người tạo mới có thể hủy yêu cầu'}, status=403)
            maintenance_request.cancel()
            message = 'Đã hủy yêu cầu bảo trì.'

        elif action == 'start_progress':
            if not is_admin_or_staff(request.user):
                return JsonResponse({'status': 'error', 'message': 'Không có quyền thực hiện hành động này'},
                                    status=403)
            maintenance_request.start_progress()
            message = 'Đã cập nhật trạng thái sang "Đang xử lý".'

        elif action == 'complete':
            if not is_admin_or_staff(request.user):
                return JsonResponse({'status': 'error', 'message': 'Không có quyền thực hiện hành động này'},
                                    status=403)
            maintenance_request.complete()
            message = 'Đã hoàn thành yêu cầu bảo trì.'

        elif action == 'reject':
            if not is_admin_or_staff(request.user):
                return JsonResponse({'status': 'error', 'message': 'Không có quyền thực hiện hành động này'},
                                    status=403)
            maintenance_request.reject(notes)
            message = 'Đã từ chối yêu cầu bảo trì.'

        else:
            return JsonResponse({'status': 'error', 'message': 'Hành động không hợp lệ'}, status=400)

        if notes:
            MaintenanceComment.objects.create(
                maintenance_request=maintenance_request,
                user=request.user,
                comment=f'Cập nhật trạng thái: {maintenance_request.get_status_display()}. Ghi chú: {notes}'
            )

        return JsonResponse({
            'status': 'success',
            'message': message,
            'new_status': maintenance_request.status,
            'new_status_display': maintenance_request.get_status_display()
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)