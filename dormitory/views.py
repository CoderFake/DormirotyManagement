
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.db.models import Q, Count

from accounts.views import is_admin_or_staff
from .models import Building, RoomType, Room, Bed, Amenity, RoomAmenity
from .forms import (
    BuildingForm, RoomTypeForm, RoomForm, BedForm, AmenityForm, RoomAmenityForm
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