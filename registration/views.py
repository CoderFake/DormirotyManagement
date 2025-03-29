from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from dormitory.models import Bed, Building, RoomType, Room
from registration.models import RoomRegistration, RegistrationPeriod, Contract


@login_required
def room_list_view(request):
    """Xem danh sách phòng có thể đăng ký"""
    current_period = RegistrationPeriod.objects.filter(
        status='active',
        is_active=True,
        registration_start__lte=timezone.now(),
        registration_end__gte=timezone.now()
    ).first()

    if not current_period:
        messages.info(request, 'Hiện tại không có kỳ đăng ký nào đang mở.')
        return redirect('dashboard:index')

    buildings = Building.objects.filter(is_active=True)

    building_id = request.GET.get('building')
    room_type_id = request.GET.get('room_type')

    rooms = Room.objects.filter(is_active=True, status__in=['available', 'partially_occupied'])

    if building_id:
        rooms = rooms.filter(building_id=building_id)

    if room_type_id:
        rooms = rooms.filter(room_type_id=room_type_id)

    room_types = RoomType.objects.filter(is_active=True)

    context = {
        'rooms': rooms,
        'buildings': buildings,
        'room_types': room_types,
        'current_period': current_period,
        'selected_building': building_id,
        'selected_room_type': room_type_id,
        'page_title': 'Danh sách phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Danh sách phòng', 'url': None}
        ]
    }
    return render(request, 'registration/room_list.html', context)


@login_required
def room_detail_view(request, room_id):
    """Xem chi tiết phòng"""
    room = get_object_or_404(Room, pk=room_id, is_active=True)

    existing_registration = RoomRegistration.objects.filter(
        user=request.user,
        status__in=['pending', 'approved', 'confirmed']
    ).exists()

    current_contract = Contract.objects.filter(
        user=request.user,
        status='active',
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).exists()

    can_register = not (existing_registration or current_contract)
    available_beds = Bed.objects.filter(room=room, status='available')
    room_amenities = room.room_amenities.all()

    context = {
        'room': room,
        'available_beds': available_beds,
        'room_amenities': room_amenities,
        'can_register': can_register,
        'page_title': f'Chi tiết phòng {room.building.name} - {room.room_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Danh sách phòng', 'url': reverse('registration:room_list')},
            {'title': f'{room.building.name} - {room.room_number}', 'url': None}
        ]
    }
    return render(request, 'registration/room_detail.html', context)


@login_required
def apply_view(request, room_id=None):

    existing_registration = RoomRegistration.objects.filter(
        user=request.user,
        status__in=['pending', 'approved', 'confirmed']
    ).first()

    current_contract = Contract.objects.filter(
        user=request.user,
        status='active',
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).first()

    if existing_registration:
        messages.warning(request, 'Bạn đã có đơn đăng ký đang chờ xử lý.')
        return redirect('registration:my_applications')

    if current_contract:
        messages.warning(request, 'Bạn đang có hợp đồng ký túc xá đang hoạt động.')
        return redirect('dashboard:index')

    current_period = RegistrationPeriod.objects.filter(
        status='active',
        is_active=True,
        registration_start__lte=timezone.now(),
        registration_end__gte=timezone.now()
    ).first()

    if not current_period:
        messages.info(request, 'Hiện tại không có kỳ đăng ký nào đang mở.')
        return redirect('dashboard:index')

    if room_id:
        room = get_object_or_404(Room, pk=room_id, is_active=True)
        if room.status in ['fully_occupied', 'unavailable', 'maintenance']:
            messages.error(request, 'Phòng này hiện không có sẵn để đăng ký.')
            return redirect('registration:room_list')
    else:
        room = None

    if request.method == 'POST':
        if not room_id:
            room_id = request.POST.get('room')
            room = get_object_or_404(Room, pk=room_id, is_active=True)

        bed_id = request.POST.get('bed')
        if not bed_id:
            messages.error(request, 'Vui lòng chọn giường.')
            return redirect('registration:apply', room_id=room_id)

        bed = get_object_or_404(Bed, pk=bed_id, room=room, status='available')

        special_requirements = request.POST.get('special_requirements', '')

        registration = RoomRegistration.objects.create(
            user=request.user,
            registration_period=current_period,
            preferred_building=room.building,
            preferred_room_type=room.room_type,
            assigned_room=room,
            assigned_bed=bed,
            special_requirements=special_requirements,
            status='pending'
        )

        messages.success(request, 'Đơn đăng ký của bạn đã được gửi thành công. Vui lòng chờ xét duyệt.')
        return redirect('registration:my_applications')

    available_beds = []
    if room:
        available_beds = Bed.objects.filter(room=room, status='available')

    buildings = Building.objects.filter(is_active=True)
    room_types = RoomType.objects.filter(is_active=True)

    context = {
        'room': room,
        'available_beds': available_beds,
        'buildings': buildings,
        'room_types': room_types,
        'current_period': current_period,
        'page_title': 'Đăng ký phòng ở',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/apply.html', context)