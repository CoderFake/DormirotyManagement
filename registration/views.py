from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from accounts.views import is_admin_or_staff
from dormitory.models import Bed, Building, RoomType, Room
from .models import RoomRegistration, RegistrationPeriod, Contract, CheckIn, CheckOut
from .forms import (
    RoomRegistrationForm, RegistrationPeriodForm, ContractForm,
    CheckInForm, CheckOutForm, ContractApprovalForm
)

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

    # Kiểm tra xem sinh viên có đủ điều kiện đăng ký không
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

    # Lấy thông tin giường còn trống
    available_beds = Bed.objects.filter(room=room, status='available')

    # Lấy thông tin tiện nghi phòng
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



@login_required
def my_applications_view(request):
    """Xem danh sách đơn đăng ký của người dùng hiện tại"""
    registrations = RoomRegistration.objects.filter(user=request.user).order_by('-registration_date')

    context = {
        'registrations': registrations,
        'page_title': 'Đơn đăng ký của tôi',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký của tôi', 'url': None}
        ]
    }
    return render(request, 'registration/my_applications.html', context)


@login_required
def my_contracts_view(request):
    """Xem danh sách hợp đồng của người dùng hiện tại"""
    contracts = Contract.objects.filter(user=request.user).order_by('-created_at')

    active_contract = contracts.filter(
        status='active',
        start_date__lte=timezone.now().date(),
        end_date__gte=timezone.now().date()
    ).first()

    context = {
        'contracts': contracts,
        'active_contract': active_contract,
        'page_title': 'Hợp đồng của tôi',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng của tôi', 'url': None}
        ]
    }
    return render(request, 'registration/my_contracts.html', context)


@login_required
def contract_detail_view(request, contract_id):
    """Xem chi tiết hợp đồng"""
    contract = get_object_or_404(Contract, pk=contract_id)

    # Kiểm tra quyền truy cập
    if not (contract.user == request.user or is_admin_or_staff(request.user)):
        messages.error(request, 'Bạn không có quyền xem hợp đồng này.')
        return redirect('registration:my_contracts')

    context = {
        'contract': contract,
        'page_title': f'Chi tiết hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng của tôi', 'url': reverse('registration:my_contracts')},
            {'title': f'#{contract.contract_number}', 'url': None}
        ]
    }
    return render(request, 'registration/contract_detail.html', context)


@login_required
def sign_contract_view(request, contract_id):
    """Ký hợp đồng (dành cho sinh viên)"""
    contract = get_object_or_404(Contract, pk=contract_id, user=request.user)

    if contract.status not in ['draft', 'pending']:
        messages.error(request, 'Hợp đồng này không thể ký.')
        return redirect('registration:contract_detail', contract_id=contract_id)

    if request.method == 'POST':
        contract.sign_by_student()
        messages.success(request, 'Bạn đã ký hợp đồng thành công.')
        return redirect('registration:contract_detail', contract_id=contract_id)

    context = {
        'contract': contract,
        'page_title': f'Ký hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng của tôi', 'url': reverse('registration:my_contracts')},
            {'title': f'#{contract.contract_number}',
             'url': reverse('registration:contract_detail', args=[contract_id])},
            {'title': 'Ký hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/sign_contract.html', context)


# ===== Views cho Admin =====

@login_required
@user_passes_test(is_admin_or_staff)
def period_list_view(request):
    """Danh sách kỳ đăng ký"""
    periods = RegistrationPeriod.objects.all().order_by('-registration_start')

    context = {
        'periods': periods,
        'page_title': 'Danh sách kỳ đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Kỳ đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/period_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def period_create_view(request):
    """Tạo kỳ đăng ký mới"""
    if request.method == 'POST':
        form = RegistrationPeriodForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tạo kỳ đăng ký mới thành công.')
            return redirect('registration:period_list')
    else:
        form = RegistrationPeriodForm()

    context = {
        'form': form,
        'page_title': 'Tạo kỳ đăng ký mới',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Kỳ đăng ký', 'url': reverse('registration:period_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'registration/period_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def period_edit_view(request, period_id):
    """Chỉnh sửa kỳ đăng ký"""
    period = get_object_or_404(RegistrationPeriod, pk=period_id)

    if request.method == 'POST':
        form = RegistrationPeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật kỳ đăng ký thành công.')
            return redirect('registration:period_list')
    else:
        form = RegistrationPeriodForm(instance=period)

    context = {
        'form': form,
        'period': period,
        'page_title': f'Chỉnh sửa kỳ đăng ký: {period.name}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Kỳ đăng ký', 'url': reverse('registration:period_list')},
            {'title': period.name, 'url': None}
        ]
    }
    return render(request, 'registration/period_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def application_list_view(request):
    """Danh sách đơn đăng ký (cho Admin)"""
    registrations = RoomRegistration.objects.all().order_by('-registration_date')

    status = request.GET.get('status')
    if status:
        registrations = registrations.filter(status=status)

    period_id = request.GET.get('period')
    if period_id:
        registrations = registrations.filter(registration_period_id=period_id)

    building_id = request.GET.get('building')
    if building_id:
        registrations = registrations.filter(preferred_building_id=building_id)

    context = {
        'registrations': registrations,
        'periods': RegistrationPeriod.objects.all(),
        'buildings': Building.objects.all(),
        'page_title': 'Danh sách đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/application_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def application_detail_view(request, application_id):
    """Chi tiết đơn đăng ký (cho Admin)"""
    registration = get_object_or_404(RoomRegistration, pk=application_id)

    context = {
        'registration': registration,
        'page_title': f'Chi tiết đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': reverse('registration:application_list')},
            {'title': registration.user.full_name, 'url': None}
        ]
    }
    return render(request, 'registration/application_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def application_approve_view(request, application_id):
    """Phê duyệt đơn đăng ký (cho Admin)"""
    registration = get_object_or_404(RoomRegistration, pk=application_id)

    if registration.status != 'pending':
        messages.error(request, 'Chỉ có thể phê duyệt đơn đang chờ xử lý.')
        return redirect('registration:application_detail', application_id=application_id)

    if request.method == 'POST':
        with transaction.atomic():
            # Cập nhật trạng thái đơn đăng ký
            registration.status = 'approved'
            registration.approval_date = timezone.now()

            if not registration.assigned_room:
                room_id = request.POST.get('room')
                if room_id:
                    registration.assigned_room = Room.objects.get(pk=room_id)

            if not registration.assigned_bed:
                bed_id = request.POST.get('bed')
                if bed_id:
                    bed = Bed.objects.get(pk=bed_id)
                    registration.assigned_bed = bed

                    # Cập nhật trạng thái giường
                    bed.status = 'reserved'
                    bed.save()

            registration.save()

            # Tạo hợp đồng mới
            contract = Contract.objects.create(
                registration=registration,
                user=registration.user,
                room=registration.assigned_room,
                bed=registration.assigned_bed,
                start_date=registration.registration_period.contract_start,
                end_date=registration.registration_period.contract_end,
                monthly_fee=registration.assigned_room.room_type.price_per_month,
                deposit_amount=registration.assigned_room.room_type.deposit,
                status='draft'
            )

            messages.success(request, 'Đã phê duyệt đơn đăng ký và tạo hợp đồng.')
            return redirect('registration:contract_list')

    # Lấy danh sách phòng và giường có sẵn
    available_rooms = Room.objects.filter(
        status__in=['available', 'partially_occupied'],
        is_active=True
    )

    if registration.assigned_room:
        available_beds = Bed.objects.filter(
            room=registration.assigned_room,
            status='available'
        )
    else:
        available_beds = []

    context = {
        'registration': registration,
        'available_rooms': available_rooms,
        'available_beds': available_beds,
        'page_title': f'Phê duyệt đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': reverse('registration:application_list')},
            {'title': registration.user.full_name,
             'url': reverse('registration:application_detail', args=[application_id])},
            {'title': 'Phê duyệt', 'url': None}
        ]
    }
    return render(request, 'registration/application_approve.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def application_reject_view(request, application_id):
    """Từ chối đơn đăng ký (cho Admin)"""
    registration = get_object_or_404(RoomRegistration, pk=application_id)

    if registration.status != 'pending':
        messages.error(request, 'Chỉ có thể từ chối đơn đang chờ xử lý.')
        return redirect('registration:application_detail', application_id=application_id)

    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        registration.reject(notes)

        messages.success(request, 'Đã từ chối đơn đăng ký.')
        return redirect('registration:application_list')

    context = {
        'registration': registration,
        'page_title': f'Từ chối đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': reverse('registration:application_list')},
            {'title': registration.user.full_name,
             'url': reverse('registration:application_detail', args=[application_id])},
            {'title': 'Từ chối', 'url': None}
        ]
    }
    return render(request, 'registration/application_reject.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_list_view(request):
    """Danh sách hợp đồng (cho Admin)"""
    contracts = Contract.objects.all().order_by('-created_at')

    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(status=status)

    building_id = request.GET.get('building')
    if building_id:
        contracts = contracts.filter(room__building_id=building_id)

    context = {
        'contracts': contracts,
        'buildings': Building.objects.all(),
        'page_title': 'Danh sách hợp đồng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/contract_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_admin_detail_view(request, contract_id):
    """Chi tiết hợp đồng (cho Admin)"""
    contract = get_object_or_404(Contract, pk=contract_id)

    context = {
        'contract': contract,
        'page_title': f'Chi tiết hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng', 'url': reverse('registration:contract_list')},
            {'title': f'#{contract.contract_number}', 'url': None}
        ]
    }
    return render(request, 'registration/contract_admin_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_approve_view(request, contract_id):
    """Ký duyệt hợp đồng (cho Admin)"""
    contract = get_object_or_404(Contract, pk=contract_id)

    if contract.status not in ['draft', 'pending']:
        messages.error(request, 'Hợp đồng này không thể ký duyệt.')
        return redirect('registration:contract_admin_detail', contract_id=contract_id)

    if request.method == 'POST':
        contract.sign_by_admin()

        # Cập nhật trạng thái giường và phòng
        if contract.bed:
            contract.bed.status = 'occupied'
            contract.bed.save()

        # Cập nhật số lượng người trong phòng
        room = contract.room
        room.current_occupancy += 1
        room.save()

        messages.success(request, 'Hợp đồng đã được ký duyệt thành công.')
        return redirect('registration:contract_admin_detail', contract_id=contract_id)

    context = {
        'contract': contract,
        'page_title': f'Ký duyệt hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng', 'url': reverse('registration:contract_list')},
            {'title': f'#{contract.contract_number}',
             'url': reverse('registration:contract_admin_detail', args=[contract_id])},
            {'title': 'Ký duyệt', 'url': None}
        ]
    }
    return render(request, 'registration/contract_approve.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_list_view(request):
    """Danh sách nhận phòng (cho Admin)"""
    check_ins = CheckIn.objects.all().order_by('-check_in_date')

    is_completed = request.GET.get('completed')
    if is_completed:
        check_ins = check_ins.filter(is_completed=(is_completed == 'true'))

    context = {
        'check_ins': check_ins,
        'page_title': 'Danh sách nhận phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Nhận phòng', 'url': None}
        ]
    }
    return render(request, 'registration/check_in_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_create_view(request, contract_id):
    """Tạo biên bản nhận phòng (cho Admin)"""
    contract = get_object_or_404(Contract, pk=contract_id)

    if contract.status != 'active':
        messages.error(request, 'Chỉ có thể tạo biên bản nhận phòng cho hợp đồng đang hoạt động.')
        return redirect('registration:contract_admin_detail', contract_id=contract_id)

    try:
        # Kiểm tra xem đã có biên bản nhận phòng chưa
        check_in = contract.check_in
        messages.warning(request, 'Hợp đồng này đã có biên bản nhận phòng.')
        return redirect('registration:check_in_detail', check_in_id=check_in.id)
    except CheckIn.DoesNotExist:
        pass

    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            check_in = form.save(commit=False)
            check_in.contract = contract
            check_in.checked_by = request.user
            check_in.save()

            messages.success(request, 'Đã tạo biên bản nhận phòng.')
            return redirect('registration:check_in_detail', check_in_id=check_in.id)
    else:
        form = CheckInForm()

    context = {
        'form': form,
        'contract': contract,
        'page_title': 'Tạo biên bản nhận phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Nhận phòng', 'url': reverse('registration:check_in_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'registration/check_in_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_detail_view(request, check_in_id):
    """Chi tiết biên bản nhận phòng (cho Admin)"""
    check_in = get_object_or_404(CheckIn, pk=check_in_id)

    context = {
        'check_in': check_in,
        'page_title': f'Chi tiết biên bản nhận phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Nhận phòng', 'url': reverse('registration:check_in_list')},
            {'title': check_in.contract.user.full_name, 'url': None}
        ]
    }
    return render(request, 'registration/check_in_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_list_view(request):
    """Danh sách trả phòng (cho Admin)"""
    check_outs = CheckOut.objects.all().order_by('-check_out_date')

    is_completed = request.GET.get('completed')
    if is_completed:
        check_outs = check_outs.filter(is_completed=(is_completed == 'true'))

    context = {
        'check_outs': check_outs,
        'page_title': 'Danh sách trả phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Trả phòng', 'url': None}
        ]
    }
    return render(request, 'registration/check_out_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_create_view(request, contract_id):
    """Tạo biên bản trả phòng (cho Admin)"""
    contract = get_object_or_404(Contract, pk=contract_id)

    try:
        # Kiểm tra xem đã có biên bản trả phòng chưa
        check_out = contract.check_out
        messages.warning(request, 'Hợp đồng này đã có biên bản trả phòng.')
        return redirect('registration:check_out_detail', check_out_id=check_out.id)
    except CheckOut.DoesNotExist:
        pass

    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            check_out = form.save(commit=False)
            check_out.contract = contract
            check_out.checked_by = request.user
            check_out.save()

            # Cập nhật trạng thái hợp đồng
            contract.status = 'terminated'
            contract.save()

            # Cập nhật trạng thái giường và phòng
            if contract.bed:
                contract.bed.status = 'available'
                contract.bed.save()

            # Cập nhật số lượng người trong phòng
            room = contract.room
            room.current_occupancy = max(0, room.current_occupancy - 1)
            room.save()

            messages.success(request, 'Đã tạo biên bản trả phòng.')
            return redirect('registration:check_out_detail', check_out_id=check_out.id)
    else:
        form = CheckOutForm()

    context = {
        'form': form,
        'contract': contract,
        'page_title': 'Tạo biên bản trả phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Trả phòng', 'url': reverse('registration:check_out_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'registration/check_out_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_detail_view(request, check_out_id):
    """Chi tiết biên bản trả phòng (cho Admin)"""
    check_out = get_object_or_404(CheckOut, pk=check_out_id)

    context = {
        'check_out': check_out,
        'page_title': f'Chi tiết biên bản trả phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Trả phòng', 'url': reverse('registration:check_out_list')},
            {'title': check_out.contract.user.full_name, 'url': None}
        ]
    }
    return render(request, 'registration/check_out_detail.html', context)