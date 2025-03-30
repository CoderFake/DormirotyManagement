from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Count
from django.db import transaction
from django.utils import timezone

from accounts.views import is_admin_or_staff
from .models import Building, RoomType, Room, Bed, Amenity, RoomAmenity
from .forms import (
    BuildingForm, RoomTypeForm, RoomForm, BedForm, AmenityForm, RoomAmenityForm,
    RoomFilterForm, BulkRoomCreateForm, BulkBedCreateForm
)

# ===== Quản lý tòa nhà =====

@login_required
@user_passes_test(is_admin_or_staff)
def building_list_view(request):
    """Danh sách tòa nhà"""
    buildings = Building.objects.all().order_by('name')

    for building in buildings:
        building.total_rooms = Room.objects.filter(building=building).count()
        building.available_rooms = Room.objects.filter(
            building=building,
            status__in=['available', 'partially_occupied']
        ).count()
        building.occupied_rooms = Room.objects.filter(
            building=building,
            status='fully_occupied'
        ).count()
        building.maintenance_rooms = Room.objects.filter(
            building=building,
            status='maintenance'
        ).count()

    context = {
        'buildings': buildings,
        'page_title': 'Danh sách tòa nhà',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tòa nhà', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def building_create_view(request):
    """Tạo tòa nhà mới"""
    if request.method == 'POST':
        form = BuildingForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo tòa nhà mới thành công.')
            return redirect('dormitory:building_list')
    else:
        form = BuildingForm()

    context = {
        'form': form,
        'page_title': 'Tạo tòa nhà mới',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tòa nhà', 'url': reverse('dormitory:building_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def building_detail_view(request, building_id):
    """Chi tiết tòa nhà"""
    building = get_object_or_404(Building, pk=building_id)
    rooms = Room.objects.filter(building=building).order_by('floor', 'room_number')

    status_stats = rooms.values('status').annotate(count=Count('id'))
    floor_stats = rooms.values('floor').annotate(count=Count('id')).order_by('floor')
    room_type_stats = rooms.values('room_type__name').annotate(count=Count('id'))

    context = {
        'building': building,
        'rooms': rooms,
        'status_stats': status_stats,
        'floor_stats': floor_stats,
        'room_type_stats': room_type_stats,
        'page_title': f'Chi tiết tòa nhà: {building.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tòa nhà', 'url': reverse('dormitory:building_list')},
            {'title': building.name, 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def building_edit_view(request, building_id):
    """Chỉnh sửa tòa nhà"""
    building = get_object_or_404(Building, pk=building_id)

    if request.method == 'POST':
        form = BuildingForm(request.POST, request.FILES, instance=building)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật tòa nhà thành công.')
            return redirect('dormitory:building_detail', building_id=building.id)
    else:
        form = BuildingForm(instance=building)

    context = {
        'form': form,
        'building': building,
        'page_title': f'Chỉnh sửa tòa nhà: {building.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tòa nhà', 'url': reverse('dormitory:building_list')},
            {'title': building.name, 'url': reverse('dormitory:building_detail', args=[building_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def building_delete_view(request, building_id):
    """Xóa tòa nhà"""
    building = get_object_or_404(Building, pk=building_id)

    if request.method == 'POST':
        building_name = building.name
        try:
            building.delete()
            messages.success(request, f'Đã xóa tòa nhà: {building_name}')
        except Exception as e:
            messages.error(request, f'Không thể xóa tòa nhà vì lỗi: {str(e)}')
        return redirect('dormitory:building_list')

    context = {
        'building': building,
        'page_title': f'Xóa tòa nhà: {building.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tòa nhà', 'url': reverse('dormitory:building_list')},
            {'title': building.name, 'url': reverse('dormitory:building_detail', args=[building_id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_delete.html', context)


# ===== Quản lý loại phòng =====

@login_required
@user_passes_test(is_admin_or_staff)
def room_type_list_view(request):
    """Danh sách loại phòng"""
    room_types = RoomType.objects.all().order_by('name')

    context = {
        'room_types': room_types,
        'page_title': 'Danh sách loại phòng',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Loại phòng', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_type_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_type_create_view(request):
    """Tạo loại phòng mới"""
    if request.method == 'POST':
        form = RoomTypeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo loại phòng mới thành công.')
            return redirect('dormitory:room_type_list')
    else:
        form = RoomTypeForm()

    context = {
        'form': form,
        'page_title': 'Tạo loại phòng mới',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Loại phòng', 'url': reverse('dormitory:room_type_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_type_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_type_detail_view(request, room_type_id):
    """Chi tiết loại phòng"""
    room_type = get_object_or_404(RoomType, pk=room_type_id)
    rooms = Room.objects.filter(room_type=room_type).order_by('building__name', 'room_number')

    context = {
        'room_type': room_type,
        'rooms': rooms,
        'page_title': f'Chi tiết loại phòng: {room_type.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Loại phòng', 'url': reverse('dormitory:room_type_list')},
            {'title': room_type.name, 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_type_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_type_edit_view(request, room_type_id):
    """Chỉnh sửa loại phòng"""
    room_type = get_object_or_404(RoomType, pk=room_type_id)

    if request.method == 'POST':
        form = RoomTypeForm(request.POST, request.FILES, instance=room_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật loại phòng thành công.')
            return redirect('dormitory:room_type_detail', room_type_id=room_type.id)
    else:
        form = RoomTypeForm(instance=room_type)

    context = {
        'form': form,
        'room_type': room_type,
        'page_title': f'Chỉnh sửa loại phòng: {room_type.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Loại phòng', 'url': reverse('dormitory:room_type_list')},
            {'title': room_type.name, 'url': reverse('dormitory:room_type_detail', args=[room_type_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_type_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_type_delete_view(request, room_type_id):
    """Xóa loại phòng"""
    room_type = get_object_or_404(RoomType, pk=room_type_id)

    if request.method == 'POST':
        room_type_name = room_type.name
        try:
            room_type.delete()
            messages.success(request, f'Đã xóa loại phòng: {room_type_name}')
        except Exception as e:
            messages.error(request, f'Không thể xóa loại phòng vì lỗi: {str(e)}')
        return redirect('dormitory:room_type_list')

    context = {
        'room_type': room_type,
        'page_title': f'Xóa loại phòng: {room_type.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Loại phòng', 'url': reverse('dormitory:room_type_list')},
            {'title': room_type.name, 'url': reverse('dormitory:room_type_detail', args=[room_type_id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_type_delete.html', context)


# ===== Quản lý phòng =====

@login_required
@user_passes_test(is_admin_or_staff)
def room_list_view(request):
    """Danh sách phòng"""
    rooms = Room.objects.all().select_related('building', 'room_type').order_by('building__name', 'floor', 'room_number')

    building_id = request.GET.get('building')
    room_type_id = request.GET.get('room_type')
    status = request.GET.get('status')
    is_active = request.GET.get('is_active')
    floor = request.GET.get('floor')

    if building_id:
        rooms = rooms.filter(building_id=building_id)
    if room_type_id:
        rooms = rooms.filter(room_type_id=room_type_id)
    if status:
        rooms = rooms.filter(status=status)
    if is_active is not None:
        is_active = is_active.lower() == 'true'
        rooms = rooms.filter(is_active=is_active)
    if floor:
        rooms = rooms.filter(floor=floor)

    context = {
        'rooms': rooms,
        'page_title': 'Danh sách phòng',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_create_view(request):
    """Tạo phòng mới"""
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo phòng mới thành công.')
            return redirect('dormitory:room_list')
    else:
        form = RoomForm()

    context = {
        'form': form,
        'page_title': 'Tạo phòng mới',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_detail_view(request, room_id):
    """Chi tiết phòng"""
    room = get_object_or_404(Room, pk=room_id)

    context = {
        'room': room,
        'page_title': f'Chi tiết phòng: {room.building.name} - {room.room_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_list')},
            {'title': f'{room.building.name} - {room.room_number}', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_edit_view(request, room_id):
    """Chỉnh sửa phòng"""
    room = get_object_or_404(Room, pk=room_id)

    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật phòng thành công.')
            return redirect('dormitory:room_detail', room_id=room.id)
    else:
        form = RoomForm(instance=room)

    context = {
        'form': form,
        'room': room,
        'page_title': f'Chỉnh sửa phòng: {room.building.name} - {room.room_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_list')},
            {'title': f'{room.building.name} - {room.room_number}', 'url': reverse('dormitory:room_detail', args=[room_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_delete_view(request, room_id):
    """Xóa phòng"""
    room = get_object_or_404(Room, pk=room_id)

    if request.method == 'POST':
        room_name = f'{room.building.name} - {room.room_number}'
        try:
            room.delete()
            messages.success(request, f'Đã xóa phòng: {room_name}')
        except Exception as e:
            messages.error(request, f'Không thể xóa phòng vì lỗi: {str(e)}')
        return redirect('dormitory:room_list')

    context = {
        'room': room,
        'page_title': f'Xóa phòng: {room.building.name} - {room.room_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_list')},
            {'title': f'{room.building.name} - {room.room_number}', 'url': reverse('dormitory:room_detail', args=[room_id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_delete.html', context)

# ===== Quản lý tòa nhà =====

@login_required
@user_passes_test(is_admin_or_staff)
def building_list_view(request):
    """Danh sách tòa nhà"""
    buildings = Building.objects.all().order_by('name')

    for building in buildings:
        building.total_rooms = Room.objects.filter(building=building).count()
        building.available_rooms = Room.objects.filter(
            building=building,
            status__in=['available', 'partially_occupied']
        ).count()
        building.occupied_rooms = Room.objects.filter(
            building=building,
            status='fully_occupied'
        ).count()
        building.maintenance_rooms = Room.objects.filter(
            building=building,
            status='maintenance'
        ).count()

    context = {
        'buildings': buildings,
        'page_title': 'Danh sách tòa nhà',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': 'Tạo hàng loạt', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/building_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bed_detail_view(request, bed_id):
    """Chi tiết giường"""
    bed = get_object_or_404(Bed, pk=bed_id)

    from registration.models import Contract
    active_contract = Contract.objects.filter(
        bed=bed,
        status='active'
    ).first()

    context = {
        'bed': bed,
        'active_contract': active_contract,
        'page_title': f'Chi tiết giường: {bed.room.building.name} - {bed.room.room_number} - Giường {bed.bed_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': f'Giường {bed.bed_number}', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bed_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bed_edit_view(request, bed_id):
    """Chỉnh sửa giường"""
    bed = get_object_or_404(Bed, pk=bed_id)

    if request.method == 'POST':
        form = BedForm(request.POST, instance=bed)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật giường thành công.')
            return redirect('dormitory:bed_detail', bed_id=bed.id)
    else:
        form = BedForm(instance=bed)

    context = {
        'form': form,
        'bed': bed,
        'page_title': f'Chỉnh sửa giường: {bed.room.building.name} - {bed.room.room_number} - Giường {bed.bed_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': f'Giường {bed.bed_number}', 'url': reverse('dormitory:bed_detail', args=[bed_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bed_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bed_delete_view(request, bed_id):
    """Xóa giường"""
    bed = get_object_or_404(Bed, pk=bed_id)

    # Kiểm tra xem giường có đang được sử dụng không
    from registration.models import Contract
    has_active_contract = Contract.objects.filter(
        bed=bed,
        status__in=['active', 'pending']
    ).exists()

    if has_active_contract:
        messages.error(request, 'Không thể xóa giường này vì đang có sinh viên sử dụng.')
        return redirect('dormitory:bed_detail', bed_id=bed.id)

    if request.method == 'POST':
        room_id = bed.room.id
        bed_name = f'Giường {bed.bed_number} - Phòng {bed.room.building.name} {bed.room.room_number}'
        try:
            bed.delete()
            messages.success(request, f'Đã xóa {bed_name}')
        except Exception as e:
            messages.error(request, f'Không thể xóa giường vì lỗi: {str(e)}')
        return redirect('dormitory:room_detail', room_id=room_id)

    context = {
        'bed': bed,
        'page_title': f'Xóa giường: {bed.room.building.name} - {bed.room.room_number} - Giường {bed.bed_number}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': f'Giường {bed.bed_number}', 'url': reverse('dormitory:bed_detail', args=[bed_id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bed_delete.html', context)


# ===== Quản lý tiện nghi =====

@login_required
@user_passes_test(is_admin_or_staff)
def amenity_list_view(request):
    """Danh sách tiện nghi"""
    amenities = Amenity.objects.all().order_by('name')

    context = {
        'amenities': amenities,
        'page_title': 'Danh sách tiện nghi',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/amenity_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def amenity_create_view(request):
    """Tạo tiện nghi mới"""
    if request.method == 'POST':
        form = AmenityForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo tiện nghi mới thành công.')
            return redirect('dormitory:amenity_list')
    else:
        form = AmenityForm()

    context = {
        'form': form,
        'page_title': 'Tạo tiện nghi mới',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi', 'url': reverse('dormitory:amenity_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/amenity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def amenity_edit_view(request, amenity_id):
    """Chỉnh sửa tiện nghi"""
    amenity = get_object_or_404(Amenity, pk=amenity_id)

    if request.method == 'POST':
        form = AmenityForm(request.POST, instance=amenity)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật tiện nghi thành công.')
            return redirect('dormitory:amenity_list')
    else:
        form = AmenityForm(instance=amenity)

    context = {
        'form': form,
        'amenity': amenity,
        'page_title': f'Chỉnh sửa tiện nghi: {amenity.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi', 'url': reverse('dormitory:amenity_list')},
            {'title': amenity.name, 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/amenity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def amenity_delete_view(request, amenity_id):
    """Xóa tiện nghi"""
    amenity = get_object_or_404(Amenity, pk=amenity_id)

    has_usage = RoomAmenity.objects.filter(amenity=amenity).exists()

    if has_usage:
        messages.error(request, 'Không thể xóa tiện nghi này vì đang được sử dụng.')
        return redirect('dormitory:amenity_list')

    if request.method == 'POST':
        amenity_name = amenity.name
        try:
            amenity.delete()
            messages.success(request, f'Đã xóa tiện nghi: {amenity_name}')
        except Exception as e:
            messages.error(request, f'Không thể xóa tiện nghi vì lỗi: {str(e)}')
        return redirect('dormitory:amenity_list')

    context = {
        'amenity': amenity,
        'page_title': f'Xóa tiện nghi: {amenity.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi', 'url': reverse('dormitory:amenity_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/amenity_delete.html', context)


# ===== API =====

@login_required
@user_passes_test(is_admin_or_staff)
def api_get_beds(request):
    """API lấy danh sách giường theo phòng"""
    room_id = request.GET.get('room_id')
    if not room_id:
        return JsonResponse({'error': 'Thiếu room_id'}, status=400)

    try:
        beds = Bed.objects.filter(
            room_id=room_id,
            status='available',
            is_active=True
        ).values('id', 'bed_number')
        return JsonResponse({'beds': list(beds)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin_or_staff)
def api_get_rooms(request):
    """API lấy danh sách phòng theo tòa nhà và loại phòng"""
    building_id = request.GET.get('building_id')
    room_type_id = request.GET.get('room_type_id')

    rooms = Room.objects.filter(
        is_active=True,
        status__in=['available', 'partially_occupied']
    )

    if building_id:
        rooms = rooms.filter(building_id=building_id)
    if room_type_id:
        rooms = rooms.filter(room_type_id=room_type_id)

    rooms_data = []
    for room in rooms:
        rooms_data.append({
            'id': str(room.id),
            'room_number': room.room_number,
            'building_name': room.building.name,
            'floor': room.floor,
            'status': room.get_status_display(),
            'available_beds': Bed.objects.filter(room=room, status='available', is_active=True).count()
        })

    return JsonResponse({'rooms': rooms_data})


@login_required
@user_passes_test(is_admin_or_staff)
def room_amenity_list_view(request):
    """Danh sách tiện nghi phòng"""
    room_amenities = RoomAmenity.objects.all().select_related('room', 'amenity')

    room_id = request.GET.get('room')
    if room_id:
        room_amenities = room_amenities.filter(room_id=room_id)

    amenity_id = request.GET.get('amenity')
    if amenity_id:
        room_amenities = room_amenities.filter(amenity_id=amenity_id)

    context = {
        'room_amenities': room_amenities,
        'rooms': Room.objects.all(),
        'amenities': Amenity.objects.all(),
        'page_title': 'Tiện nghi phòng',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi phòng', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_amenity_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_amenity_create_view(request):
    """Thêm tiện nghi cho phòng"""
    if request.method == 'POST':
        form = RoomAmenityForm(request.POST)
        if form.is_valid():
            room_amenity = form.save()
            messages.success(request, 'Đã thêm tiện nghi cho phòng thành công.')
            return redirect('dormitory:room_detail', room_id=room_amenity.room.id)
    else:
        room_id = request.GET.get('room')
        initial_data = {}
        if room_id:
            try:
                room = Room.objects.get(pk=room_id)
                initial_data['room'] = room
            except Room.DoesNotExist:
                pass

        form = RoomAmenityForm(initial=initial_data)

    context = {
        'form': form,
        'page_title': 'Thêm tiện nghi cho phòng',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi phòng', 'url': reverse('dormitory:room_amenity_list')},
            {'title': 'Thêm mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_amenity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_amenity_edit_view(request, room_amenity_id):
    """Chỉnh sửa tiện nghi phòng"""
    room_amenity = get_object_or_404(RoomAmenity, pk=room_amenity_id)

    if request.method == 'POST':
        form = RoomAmenityForm(request.POST, instance=room_amenity)
        if form.is_valid():
            room_amenity = form.save()
            messages.success(request, 'Cập nhật tiện nghi phòng thành công.')
            return redirect('dormitory:room_detail', room_id=room_amenity.room.id)
    else:
        form = RoomAmenityForm(instance=room_amenity)

    context = {
        'form': form,
        'room_amenity': room_amenity,
        'page_title': f'Cập nhật tiện nghi: {room_amenity.amenity.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Tiện nghi phòng', 'url': reverse('dormitory:room_amenity_list')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_amenity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def room_amenity_delete_view(request, room_amenity_id):
    """Xóa tiện nghi phòng"""
    room_amenity = get_object_or_404(RoomAmenity, pk=room_amenity_id)
    room_id = room_amenity.room.id

    if request.method == 'POST':
        room_amenity.delete()
        messages.success(request, f'Đã xóa tiện nghi {room_amenity.amenity.name} khỏi phòng.')
        return redirect('dormitory:room_detail', room_id=room_id)

    context = {
        'room_amenity': room_amenity,
        'page_title': f'Xóa tiện nghi: {room_amenity.amenity.name}',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_detail', args=[room_id])},
            {'title': 'Xóa tiện nghi', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/room_amenity_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bulk_room_create_view(request):
    """Tạo nhiều phòng cùng lúc"""
    if request.method == 'POST':
        form = BulkRoomCreateForm(request.POST)
        if form.is_valid():
            building = form.cleaned_data['building']
            room_type = form.cleaned_data['room_type']
            floor = form.cleaned_data['floor']
            start_number = form.cleaned_data['start_number']
            end_number = form.cleaned_data['end_number']
            room_prefix = form.cleaned_data.get('room_prefix', '')

            created_count = 0
            with transaction.atomic():
                for i in range(start_number, end_number + 1):
                    room_number = f"{room_prefix}{i}" if room_prefix else str(i)

                    # Kiểm tra xem phòng đã tồn tại chưa
                    if Room.objects.filter(building=building, room_number=room_number).exists():
                        continue

                    room = Room.objects.create(
                        building=building,
                        room_type=room_type,
                        room_number=room_number,
                        floor=floor,
                        status='available',
                        current_occupancy=0,
                        is_active=True
                    )

                    # Tạo giường theo sức chứa
                    capacity = room_type.capacity
                    for j in range(1, capacity + 1):
                        Bed.objects.create(
                            room=room,
                            bed_number=f"{j}",
                            status="available",
                            is_active=True
                        )

                    created_count += 1

            if created_count > 0:
                messages.success(request,
                                 f'Đã tạo thành công {created_count} phòng và {created_count * room_type.capacity} giường.')
            else:
                messages.warning(request, 'Không có phòng nào được tạo. Có thể các phòng đã tồn tại.')

            return redirect('dormitory:room_list')
    else:
        form = BulkRoomCreateForm()

    context = {
        'form': form,
        'page_title': 'Tạo nhiều phòng',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Phòng', 'url': reverse('dormitory:room_list')},
            {'title': 'Tạo hàng loạt', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bulk_room_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bed_list_view(request):
    """Danh sách giường"""
    room_id = request.GET.get('room')
    status = request.GET.get('status')
    is_active = request.GET.get('is_active')

    beds = Bed.objects.all().select_related('room', 'room__building', 'room__room_type').order_by(
        'room__building__name', 'room__room_number', 'bed_number'
    )

    if room_id:
        beds = beds.filter(room_id=room_id)
    if status:
        beds = beds.filter(status=status)
    if is_active is not None:
        is_active = is_active.lower() == 'true'
        beds = beds.filter(is_active=is_active)

    for bed in beds:
        from registration.models import Contract
        bed.current_contract = Contract.objects.filter(
            bed=bed,
            status='active',
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).first()

    context = {
        'beds': beds,
        'rooms': Room.objects.all().select_related('building'),
        'page_title': 'Danh sách giường',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bed_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bed_create_view(request):
    """Tạo giường mới"""
    if request.method == 'POST':
        form = BedForm(request.POST)
        if form.is_valid():
            bed = form.save()
            messages.success(request, 'Tạo giường mới thành công.')
            return redirect('dormitory:room_detail', room_id=bed.room.id)
    else:
        room_id = request.GET.get('room')
        initial_data = {}
        if room_id:
            try:
                room = Room.objects.get(pk=room_id)
                initial_data['room'] = room
            except Room.DoesNotExist:
                pass

        form = BedForm(initial=initial_data)

    context = {
        'form': form,
        'page_title': 'Tạo giường mới',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bed_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bulk_bed_create_view(request):
    """Tạo nhiều giường cùng lúc"""
    if request.method == 'POST':
        form = BulkBedCreateForm(request.POST)
        if form.is_valid():
            room = form.cleaned_data['room']
            quantity = form.cleaned_data['quantity']
            bed_prefix = form.cleaned_data.get('bed_prefix', '')

            max_beds = room.room_type.capacity

            existing_beds = Bed.objects.filter(room=room).count()
            if existing_beds + quantity > max_beds:
                messages.error(request,
                               f'Không thể thêm {quantity} giường. Phòng chỉ có thể chứa tối đa {max_beds} giường (hiện tại có {existing_beds} giường).')
                return redirect('dormitory:room_detail', room_id=room.id)

            created_count = 0
            with transaction.atomic():
                for i in range(1, quantity + 1):
                    bed_number = f"{bed_prefix}{existing_beds + i}" if bed_prefix else f"{existing_beds + i}"

                    if Bed.objects.filter(room=room, bed_number=bed_number).exists():
                        continue

                    Bed.objects.create(
                        room=room,
                        bed_number=bed_number,
                        status="available",
                        is_active=True
                    )
                    created_count += 1

            if created_count > 0:
                messages.success(request, f'Đã tạo thành công {created_count} giường trong phòng {room}.')
            else:
                messages.warning(request, 'Không có giường nào được tạo. Có thể các giường đã tồn tại.')

            return redirect('dormitory:room_detail', room_id=room.id)
    else:
        room_id = request.GET.get('room')
        initial_data = {}
        if room_id:
            try:
                room = Room.objects.get(pk=room_id)
                initial_data['room'] = room
            except Room.DoesNotExist:
                pass

        form = BulkBedCreateForm(initial=initial_data)

    context = {
        'form': form,
        'page_title': 'Tạo nhiều giường',
        'breadcrumbs': [
            {'title': 'Quản lý ký túc xá', 'url': '#'},
            {'title': 'Giường', 'url': reverse('dormitory:bed_list')},
            {'title': 'Tạo hàng loạt', 'url': None}
        ]
    }
    return render(request, 'dormitory/admin/bulk_bed_form.html', context)


#===========Dành cho sinh viên=============

@login_required
def room_public_list_view(request):
    """Danh sách phòng công khai cho sinh viên xem"""
    rooms = Room.objects.filter(
        is_active=True,
        status__in=['available', 'partially_occupied']
    ).select_related('building', 'room_type')

    building_id = request.GET.get('building')
    if building_id:
        rooms = rooms.filter(building_id=building_id)

    room_type_id = request.GET.get('room_type')
    if room_type_id:
        rooms = rooms.filter(room_type_id=room_type_id)

    gender = request.GET.get('gender')
    if gender:
        rooms = rooms.filter(
            room_type__gender_allowed__in=[gender, 'mixed']
        )

    search = request.GET.get('search')
    if search:
        rooms = rooms.filter(
            Q(room_number__icontains=search) |
            Q(building__name__icontains=search) |
            Q(room_type__name__icontains=search)
        )

    for room in rooms:
        room.available_beds_count = Bed.objects.filter(
            room=room,
            status='available',
            is_active=True
        ).count()

    context = {
        'rooms': rooms,
        'buildings': Building.objects.filter(is_active=True),
        'room_types': RoomType.objects.filter(is_active=True),
        'page_title': 'Danh sách phòng',
        'breadcrumbs': [
            {'title': 'Phòng ở', 'url': None}
        ]
    }
    return render(request, 'dormitory/room_list.html', context)


@login_required
def room_public_detail_view(request, room_id):
    """Chi tiết phòng (cho sinh viên xem)"""
    room = get_object_or_404(Room, pk=room_id, is_active=True)

    gender_allowed = room.room_type.gender_allowed
    user_gender = request.user.gender

    if gender_allowed != 'mixed' and gender_allowed != user_gender:
        messages.warning(request, f'Phòng này chỉ dành cho sinh viên {gender_allowed}.')

    available_beds = Bed.objects.filter(
        room=room,
        status='available',
        is_active=True
    )

    room_amenities = RoomAmenity.objects.filter(room=room).select_related('amenity')

    context = {
        'room': room,
        'available_beds': available_beds,
        'room_amenities': room_amenities,
        'page_title': f'Chi tiết phòng: {room.building.name} - {room.room_number}',
        'breadcrumbs': [
            {'title': 'Phòng ở', 'url': reverse('dormitory:room_public_list')},
            {'title': f'{room.building.name} - {room.room_number}', 'url': None}
        ]
    }
    return render(request, 'dormitory/room_detail.html', context)


@login_required
def building_public_list_view(request):
    """Danh sách tòa nhà (cho sinh viên xem)"""
    buildings = Building.objects.filter(is_active=True).order_by('name')

    for building in buildings:
        building.total_rooms = Room.objects.filter(building=building).count()
        building.available_rooms = Room.objects.filter(
            building=building,
            status__in=['available', 'partially_occupied']
        ).count()

    context = {
        'buildings': buildings,
        'page_title': 'Danh sách tòa nhà',
        'breadcrumbs': [
            {'title': 'Tòa nhà', 'url': None}
        ]
    }
    return render(request, 'dormitory/building_list.html', context)


@login_required
def building_public_detail_view(request, building_id):
    """Chi tiết tòa nhà (cho sinh viên xem)"""
    building = get_object_or_404(Building, pk=building_id, is_active=True)

    rooms = Room.objects.filter(
        building=building,
        is_active=True,
        status__in=['available', 'partially_occupied']
    )

    if request.user.user_type == 'student':
        user_gender = request.user.gender
        rooms = rooms.filter(
            Q(room_type__gender_allowed='mixed') |
            Q(room_type__gender_allowed=user_gender)
        )

    # Tính số giường trống cho mỗi phòng
    for room in rooms:
        room.available_beds_count = Bed.objects.filter(
            room=room,
            status='available',
            is_active=True
        ).count()

    context = {
        'building': building,
        'rooms': rooms,
        'page_title': f'Chi tiết tòa nhà: {building.name}',
        'breadcrumbs': [
            {'title': 'Tòa nhà', 'url': reverse('dormitory:building_public_list')},
            {'title': building.name, 'url': None}
        ]
    }
    return render(request, 'dormitory/building_detail.html', context)


@login_required
def room_type_public_list_view(request):
    """Danh sách loại phòng (cho sinh viên xem)"""
    room_types = RoomType.objects.filter(is_active=True).order_by('price_per_month')

    if request.user.user_type == 'student':
        user_gender = request.user.gender
        room_types = room_types.filter(
            Q(gender_allowed='mixed') |
            Q(gender_allowed=user_gender)
        )

    context = {
        'room_types': room_types,
        'page_title': 'Loại phòng',
        'breadcrumbs': [
            {'title': 'Loại phòng', 'url': None}
        ]
    }
    return render(request, 'dormitory/room_type_list.html', context)


@login_required
def room_type_public_detail_view(request, room_type_id):
    """Chi tiết loại phòng (cho sinh viên xem)"""
    room_type = get_object_or_404(RoomType, pk=room_type_id, is_active=True)

    if request.user.user_type == 'student':
        user_gender = request.user.gender
        if room_type.gender_allowed != 'mixed' and room_type.gender_allowed != user_gender:
            messages.warning(request,
                             f'Loại phòng này chỉ dành cho sinh viên {room_type.get_gender_allowed_display()}.')

    rooms = Room.objects.filter(
        room_type=room_type,
        is_active=True,
        status__in=['available', 'partially_occupied']
    ).select_related('building')

    context = {
        'room_type': room_type,
        'rooms': rooms,
        'page_title': f'Chi tiết loại phòng: {room_type.name}',
        'breadcrumbs': [
            {'title': 'Loại phòng', 'url': reverse('dormitory:room_type_public_list')},
            {'title': room_type.name, 'url': None}
        ]
    }
    return render(request, 'dormitory/room_type_detail.html', context)
