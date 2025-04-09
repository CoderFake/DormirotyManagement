from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import base64
from django.core.files.base import ContentFile

from accounts.views import is_admin_or_staff
from dormitory.models import Bed, Building, RoomType, Room
from notification.models import NotificationCategory, Notification, UserNotification
from payment.models.base import Invoice
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


    building_id = request.GET.get('building')
    room_type_id = request.GET.get('room_type')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'room_number') 
    gender = request.GET.get('gender')


    rooms = Room.objects.filter(
        is_active=True,
        status__in=['available', 'partially_occupied']
    ).select_related('building', 'room_type')


    if building_id:
        rooms = rooms.filter(building_id=building_id)

    if room_type_id:
        rooms = rooms.filter(room_type_id=room_type_id)

    if gender:
        rooms = rooms.filter(gender=gender)

    if search_query:
        rooms = rooms.filter(
            Q(room_number__icontains=search_query) |
            Q(building__name__icontains=search_query) |
            Q(room_type__name__icontains=search_query)
        )


    rooms = rooms.annotate(
        available_beds_count=Count(
            'beds',
            filter=Q(beds__status='available')
        )
    )


    if sort_by == 'price':
        rooms = rooms.order_by('room_type__price_per_month')
    elif sort_by == 'available_beds':
        rooms = rooms.order_by('-available_beds_count')
    elif sort_by == 'building':
        rooms = rooms.order_by('building__name', 'room_number')
    else:
        rooms = rooms.order_by('room_number')


    paginator = Paginator(rooms, 10)
    page_number = request.GET.get('page', 1)
    rooms_page = paginator.get_page(page_number)


    buildings = Building.objects.filter(is_active=True)
    room_types = RoomType.objects.filter(is_active=True)

    context = {
        'rooms': rooms_page,
        'buildings': buildings,
        'room_types': room_types,
        'current_period': current_period,
        'can_register': can_register,
        'selected_building': building_id,
        'selected_room_type': room_type_id,
        'selected_gender': gender,
        'search_query': search_query,
        'sort_by': sort_by,
        'page_title': 'Danh sách phòng',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Danh sách phòng', 'url': None}
        ]
    }

    if not can_register:
        if existing_registration:
            messages.warning(request, 'Bạn đã có đơn đăng ký đang chờ xử lý.')
        elif current_contract:
            messages.warning(request, 'Bạn đang có hợp đồng ký túc xá đang hoạt động.')

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
    """Xem danh sách hợp đồng của sinh viên"""
    contracts = Contract.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'contracts': contracts,
        'page_title': 'Hợp đồng của tôi',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng của tôi', 'url': None}
        ]
    }
    return render(request, 'registration/my_contracts.html', context)


@login_required
def contract_detail_view(request, contract_id):
    is_admin = request.user.user_type in ['admin', 'staff']

    if is_admin:
        contract = get_object_or_404(Contract, pk=contract_id)
    else:
        contract = get_object_or_404(Contract, pk=contract_id, user=request.user)

    registration = contract.registration if hasattr(contract, 'registration') else None

    try:
        check_in = contract.check_in
    except:
        check_in = None

    try:
        check_out = contract.check_out
    except:
        check_out = None

    invoices = contract.invoices.all() if hasattr(contract, 'invoices') else []

    context = {
        'contract': contract,
        'registration': registration,
        'check_in': check_in,
        'check_out': check_out,
        'invoices': invoices,
        'is_admin': is_admin,
        'page_title': f'Chi tiết hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng',
             'url': reverse('registration:my_contracts') if not is_admin else reverse('registration:contract_list')},
            {'title': f'Hợp đồng #{contract.contract_number}', 'url': None}
        ]
    }
    return render(request, 'registration/contract_detail.html', context)


@login_required
def contract_sign_view(request, contract_id):
    """Hiển thị và xử lý việc ký hợp đồng của sinh viên."""
    contract = get_object_or_404(Contract, pk=contract_id, user=request.user)

    if contract.status != 'pending_signature':
        messages.warning(request, "Hợp đồng này không ở trạng thái chờ ký hoặc đã được xử lý.")
        return redirect('registration:contract_detail', contract_id=contract.id)
        
    if contract.signed_by_student:
        messages.info(request, "Bạn đã ký hợp đồng này rồi.")
        return redirect('registration:contract_detail', contract_id=contract.id)

    if request.method == 'POST':
        signature_data = request.POST.get('signature')
        if not signature_data:
            messages.error(request, "Vui lòng cung cấp chữ ký.")
            context = {
                'contract': contract,
                'page_title': f'Ký hợp đồng #{contract.contract_number}',
                'error_message': "Vui lòng cung cấp chữ ký."
            }
            return render(request, 'registration/contract_sign.html', context)

        try:
            contract.sign_by_student(signature_data)
            
            category, _ = NotificationCategory.objects.get_or_create(
                name="Hợp đồng",
                defaults={
                    'icon': 'fa-file-signature',
                    'color': 'success',
                    'description': 'Thông báo về hợp đồng thuê phòng'
                }
            )
            
            deposit_invoice = Invoice.objects.filter(contract=contract, invoice_items__fee_type__code='DEPOSIT').first()
            invoice_url = "#" 
            if deposit_invoice:
                 invoice_url = request.build_absolute_uri(
                     reverse('payment:invoice_detail', args=[deposit_invoice.id])
                 )
            
            notification_content = (
                f"Bạn đã ký thành công hợp đồng #{contract.contract_number}. "
                f"Vui lòng <a href='{invoice_url}'>thanh toán tiền cọc</a> ({contract.deposit_amount:,.0f} VNĐ) để hoàn tất đăng ký."
            )
            notification = Notification.objects.create(
                title="Đã ký hợp đồng - Chờ thanh toán cọc",
                content=notification_content,
                category=category,
                sender_id=None, 
                priority="normal",
                is_global=False,
            )
            UserNotification.objects.create(
                notification=notification,
                user=contract.user
            )

            messages.success(request, "Bạn đã ký hợp đồng thành công. Vui lòng thanh toán tiền cọc.")
            if deposit_invoice:
                return redirect('payment:invoice_detail', invoice_id=deposit_invoice.id)
            else:
                 return redirect('registration:contract_detail', contract_id=contract.id)

        except Exception as e:
            messages.error(request, f"Đã xảy ra lỗi khi lưu chữ ký: {str(e)}")
            context = {
                'contract': contract,
                'page_title': f'Ký hợp đồng #{contract.contract_number}',
                'error_message': f"Đã xảy ra lỗi khi lưu chữ ký: {str(e)}"
            }
            return render(request, 'registration/contract_sign.html', context)

    context = {
        'contract': contract,
        'page_title': f'Ký hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Hợp đồng của tôi', 'url': reverse('registration:my_contracts')},
            {'title': f'Hợp đồng #{contract.contract_number}', 'url': reverse('registration:contract_detail', args=[contract_id])},
            {'title': 'Ký hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/contract_sign.html', context)


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
    applications = RoomRegistration.objects.all().order_by('-registration_date')

    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)

    period_id = request.GET.get('period')
    if period_id:
        applications = applications.filter(registration_period_id=period_id)

    search = request.GET.get('search')
    if search:
        applications = applications.filter(
            Q(user__student_id__icontains=search) |
            Q(user__full_name__icontains=search)
        )

    context = {
        'applications': applications,
        'periods': RegistrationPeriod.objects.all(),
        'page_title': 'Danh sách đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/admin/application_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def application_detail_view(request, application_id):
    """Chi tiết đơn đăng ký (cho Admin)"""
    registration = get_object_or_404(RoomRegistration, pk=application_id)

    context = {
        'registration': registration,  
        'application': registration,  
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
    """Phê duyệt đơn đăng ký, tạo hợp đồng và hóa đơn cọc."""
    try:
        registration = get_object_or_404(RoomRegistration, pk=application_id)
    except RoomRegistration.DoesNotExist:
        messages.error(request, 'Không tìm thấy đơn đăng ký.')
        return redirect('registration:application_list')

    if registration.status != 'pending':
        messages.warning(request, 'Đơn đăng ký này không ở trạng thái chờ xử lý.')
        return redirect('registration:application_detail', application_id=application_id)

    if request.method == 'POST':
        try:
            with transaction.atomic():
                preferred_building = registration.preferred_building
                preferred_room_type = registration.preferred_room_type

                available_rooms = Room.objects.filter(
                    status__in=['available', 'partially_occupied'],
                    is_active=True
                ).select_related('building', 'room_type')

                # Lọc theo tòa nhà nếu có
                if preferred_building:
                    available_rooms = available_rooms.filter(building=preferred_building)

                # Lọc theo loại phòng nếu có
                if preferred_room_type:
                    available_rooms = available_rooms.filter(room_type=preferred_room_type)

                # Nếu không tìm thấy phòng phù hợp với lựa chọn ưu tiên, tìm bất kỳ phòng nào có sẵn
                if not available_rooms.exists():
                    available_rooms = Room.objects.filter(
                        status__in=['available', 'partially_occupied'],
                        is_active=True
                    ).select_related('building', 'room_type')
                    
                    if not available_rooms.exists():
                        messages.error(request, 'Không có phòng nào có sẵn trong hệ thống.')
                        return redirect('registration:application_detail', application_id=application_id)

                room = None
                bed = None

                # Tìm phòng có giường trống
                for r in available_rooms:
                    # Lấy giường trống đầu tiên trong phòng
                    available_bed = Bed.objects.filter(room=r, status='available').first()
                    if available_bed:
                        room = r
                        bed = available_bed
                        break

                if not room or not bed:
                    messages.error(request, 'Không tìm thấy phòng và giường phù hợp có sẵn.')
                    return redirect('registration:application_detail', application_id=application_id)

                # 2. Cập nhật đơn đăng ký
                registration.assigned_room = room
                registration.assigned_bed = bed
                registration.status = 'approved'
                registration.approval_date = timezone.now()
                registration.save(update_fields=['assigned_room', 'assigned_bed', 'status', 'approval_date'])

                # 3. Cập nhật trạng thái giường
                bed.status = 'reserved'
                bed.save(update_fields=['status'])

                # 4. Tạo hợp đồng
                monthly_fee = room.room_type.price_per_month
                deposit_amount = room.room_type.deposit

                contract = Contract.objects.create(
                    registration=registration,
                    user=registration.user,
                    room=room,
                    bed=bed,
                    start_date=registration.registration_period.contract_start,
                    end_date=registration.registration_period.contract_end,
                    monthly_fee=monthly_fee,
                    deposit_amount=deposit_amount,
                    status='pending_signature'
                )

                # 5. Gửi thông báo
                category, _ = NotificationCategory.objects.get_or_create(
                    name="Hợp đồng",
                    defaults={
                        'icon': 'fa-file-signature',
                        'color': 'info',
                        'description': 'Thông báo về hợp đồng thuê phòng'
                    }
                )
                
                sign_contract_url = request.build_absolute_uri(
                    reverse('registration:contract_sign', args=[contract.id])
                )
                
                deposit_invoice = Invoice.objects.filter(contract=contract, items__fee_type__code='DEPOSIT').first()
                invoice_url = "#"
                if deposit_invoice:
                    invoice_url = request.build_absolute_uri(
                        reverse('payment:invoice_detail', args=[deposit_invoice.id])
                    )

                notification_content = (
                    f"Đơn đăng ký của bạn đã được duyệt! Phòng: {room.building.name} - {room.room_number}, Giường: {bed.bed_number}.<br>"
                    f"Vui lòng <a href='{sign_contract_url}'>ký hợp đồng</a> và "
                    f"<a href='{invoice_url}'>thanh toán tiền cọc</a> ({deposit_amount:,.0f} VNĐ) để hoàn tất."
                )

                notification = Notification.objects.create(
                    title="Yêu cầu ký hợp đồng và thanh toán cọc",
                    content=notification_content,
                    category=category,
                    sender=request.user,
                    priority="high",
                    is_global=False,
                )

                UserNotification.objects.create(
                    notification=notification,
                    user=registration.user
                )

                messages.success(request,
                                f'Đã phê duyệt đơn đăng ký. Hợp đồng #{contract.contract_number} và hóa đơn cọc đã được tạo. Sinh viên cần ký hợp đồng và thanh toán.')
                return redirect('registration:contract_list')

        except Exception as e:
            messages.error(request, f'Đã xảy ra lỗi trong quá trình phê duyệt: {str(e)}')
            return redirect('registration:application_detail', application_id=application_id)
    
    return render(request, 'registration/application_approve.html', {
        'registration': registration,
        'page_title': f'Phê duyệt đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký', 'url': reverse('registration:application_list')},
            {'title': registration.user.full_name, 'url': reverse('registration:application_detail', args=[application_id])},
            {'title': 'Phê duyệt', 'url': None}
        ]
    })

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
    """Danh sách hợp đồng (cho admin)"""
    contracts = Contract.objects.all().select_related('user', 'room').order_by('-created_at')


    status = request.GET.get('status')
    if status:
        contracts = contracts.filter(status=status)


    search_query = request.GET.get('q')
    if search_query:
        contracts = contracts.filter(
            Q(contract_number__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__full_name__icontains=search_query)
        )


    paginator = Paginator(contracts, 20)
    page_number = request.GET.get('page', 1)
    contracts_page = paginator.get_page(page_number)

    context = {
        'contracts': contracts_page,
        'status': status,
        'search_query': search_query,
        'page_title': 'Danh sách hợp đồng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/contract_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_admin_detail_view(request, contract_id):
    """Chi tiết hợp đồng (cho admin)"""
    contract = get_object_or_404(Contract, pk=contract_id)

    context = {
        'contract': contract,
        'page_title': f'Chi tiết hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Hợp đồng', 'url': reverse('registration:contract_list')},
            {'title': f'Hợp đồng #{contract.contract_number}', 'url': None}
        ]
    }
    return render(request, 'registration/contract_admin_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_approve_view(request, contract_id):
    """Duyệt hợp đồng"""
    contract = get_object_or_404(Contract, pk=contract_id)

    if not contract.signed_by_student:
        messages.error(request, 'Sinh viên chưa ký hợp đồng.')
        return redirect('registration:contract_admin_detail', contract_id=contract.id)

    if contract.signed_by_admin:
        messages.warning(request, 'Hợp đồng này đã được duyệt.')
        return redirect('registration:contract_admin_detail', contract_id=contract.id)

    if request.method == 'POST':
        form = ContractApprovalForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.signed_by_admin = True
            contract.admin_signed_at = timezone.now()
            contract.approved_by = request.user
            contract.save()
            messages.success(request, 'Đã duyệt hợp đồng thành công.')
            return redirect('registration:contract_admin_detail', contract_id=contract.id)
    else:
        form = ContractApprovalForm(instance=contract)

    context = {
        'form': form,
        'contract': contract,
        'page_title': f'Duyệt hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Hợp đồng', 'url': reverse('registration:contract_list')},
            {'title': f'Hợp đồng #{contract.contract_number}', 'url': reverse('registration:contract_admin_detail', args=[contract_id])},
            {'title': 'Duyệt hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/contract_approve.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_list_view(request):
    """Danh sách biên bản nhận phòng"""
    check_ins = CheckIn.objects.all().select_related('contract', 'contract__user', 'contract__room').order_by('-created_at')


    is_completed = request.GET.get('is_completed')
    if is_completed is not None:
        is_completed = is_completed.lower() == 'true'
        check_ins = check_ins.filter(is_completed=is_completed)


    search_query = request.GET.get('q')
    if search_query:
        check_ins = check_ins.filter(
            Q(contract__user__username__icontains=search_query) |
            Q(contract__user__full_name__icontains=search_query) |
            Q(contract__room__room_number__icontains=search_query)
        )


    paginator = Paginator(check_ins, 20)
    page_number = request.GET.get('page', 1)
    check_ins_page = paginator.get_page(page_number)

    context = {
        'check_ins': check_ins_page,
        'is_completed': is_completed,
        'search_query': search_query,
        'page_title': 'Danh sách biên bản nhận phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản nhận phòng', 'url': None}
        ]
    }
    return render(request, 'registration/check_in_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_create_view(request, contract_id):
    """Tạo biên bản nhận phòng"""
    contract = get_object_or_404(Contract, pk=contract_id)


    if CheckIn.objects.filter(contract=contract).exists():
        messages.error(request, 'Đã có biên bản nhận phòng cho hợp đồng này.')
        return redirect('registration:check_in_list')

    if request.method == 'POST':
        form = CheckInForm(request.POST)
        if form.is_valid():
            check_in = form.save(commit=False)
            check_in.contract = contract
            check_in.checked_by = request.user
            check_in.save()
            messages.success(request, 'Đã tạo biên bản nhận phòng thành công.')
            return redirect('registration:check_in_detail', check_in_id=check_in.id)
    else:
        form = CheckInForm()

    context = {
        'form': form,
        'contract': contract,
        'page_title': 'Tạo biên bản nhận phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản nhận phòng', 'url': reverse('registration:check_in_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'registration/admin/check_in_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_in_detail_view(request, check_in_id):
    """Chi tiết biên bản nhận phòng"""
    check_in = get_object_or_404(CheckIn, pk=check_in_id)

    if request.method == 'POST':
        form = CheckInForm(request.POST, instance=check_in)
        if form.is_valid():
            check_in = form.save(commit=False)
            if not check_in.is_completed:
                check_in.is_completed = True
                check_in.completed_at = timezone.now()
                check_in.completed_by = request.user
            check_in.save()
            messages.success(request, 'Đã cập nhật biên bản nhận phòng thành công.')
            return redirect('registration:check_in_detail', check_in_id=check_in.id)
    else:
        form = CheckInForm(instance=check_in)

    context = {
        'form': form,
        'check_in': check_in,
        'page_title': 'Chi tiết biên bản nhận phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản nhận phòng', 'url': reverse('registration:check_in_list')},
            {'title': f'Biên bản #{check_in.id}', 'url': None}
        ]
    }
    return render(request, 'registration/admin/check_in_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_list_view(request):
    """Danh sách biên bản trả phòng"""
    check_outs = CheckOut.objects.all().select_related('contract', 'contract__user', 'contract__room').order_by('-created_at')


    is_completed = request.GET.get('is_completed')
    if is_completed is not None:
        is_completed = is_completed.lower() == 'true'
        check_outs = check_outs.filter(is_completed=is_completed)


    search_query = request.GET.get('q')
    if search_query:
        check_outs = check_outs.filter(
            Q(contract__user__username__icontains=search_query) |
            Q(contract__user__full_name__icontains=search_query) |
            Q(contract__room__room_number__icontains=search_query)
        )


    paginator = Paginator(check_outs, 20)
    page_number = request.GET.get('page', 1)
    check_outs_page = paginator.get_page(page_number)

    context = {
        'check_outs': check_outs_page,
        'is_completed': is_completed,
        'search_query': search_query,
        'page_title': 'Danh sách biên bản trả phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản trả phòng', 'url': None}
        ]
    }
    return render(request, 'registration/admin/check_out_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_create_view(request, contract_id):
    """Tạo biên bản trả phòng"""
    contract = get_object_or_404(Contract, pk=contract_id)


    if CheckOut.objects.filter(contract=contract).exists():
        messages.error(request, 'Đã có biên bản trả phòng cho hợp đồng này.')
        return redirect('registration:check_out_list')

    if request.method == 'POST':
        form = CheckOutForm(request.POST)
        if form.is_valid():
            check_out = form.save(commit=False)
            check_out.contract = contract
            check_out.checked_by = request.user
            check_out.save()
            messages.success(request, 'Đã tạo biên bản trả phòng thành công.')
            return redirect('registration:check_out_detail', check_out_id=check_out.id)
    else:
        form = CheckOutForm()

    context = {
        'form': form,
        'contract': contract,
        'page_title': 'Tạo biên bản trả phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản trả phòng', 'url': reverse('registration:check_out_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'registration/admin/check_out_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def contract_cancel_view(request, contract_id):
    """Hủy hợp đồng"""
    contract = get_object_or_404(Contract, pk=contract_id)
    
    if contract.status in ['terminated', 'canceled', 'expired']:
        messages.error(request, 'Không thể hủy hợp đồng đã kết thúc.')
        return redirect('registration:contract_list')
    
    if request.method == 'POST':
        notes = request.POST.get('notes')
        with transaction.atomic():
            # Cập nhật trạng thái hợp đồng
            contract.status = 'canceled'
            contract.notes = notes
            contract.save()
            
            # Giải phóng giường
            if contract.bed:
                contract.bed.status = 'available'
                contract.bed.save()
            
            # Tạo thông báo
            category, _ = NotificationCategory.objects.get_or_create(
                name="Hợp đồng",
                defaults={
                    'icon': 'fa-file-contract',
                    'color': 'danger',
                    'description': 'Thông báo về hợp đồng thuê phòng'
                }
            )
            
            notification = Notification.objects.create(
                title="Hợp đồng đã bị hủy",
                content=f"Hợp đồng #{contract.contract_number} đã bị hủy. Lý do: {notes}",
                category=category,
                sender=request.user,
                priority="high",
                is_global=False,
            )
            
            UserNotification.objects.create(
                notification=notification,
                user=contract.user
            )
            
            messages.success(request, 'Đã hủy hợp đồng thành công.')
            return redirect('registration:contract_list')
    
    context = {
        'contract': contract,
        'page_title': f'Xác nhận Hủy hợp đồng #{contract.contract_number}',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Hợp đồng', 'url': reverse('registration:contract_list')},
            {'title': 'Hủy hợp đồng', 'url': None}
        ]
    }
    return render(request, 'registration/admin/contract_cancel.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def check_out_detail_view(request, check_out_id):
    """Chi tiết biên bản trả phòng"""
    check_out = get_object_or_404(CheckOut, pk=check_out_id)

    if request.method == 'POST':
        form = CheckOutForm(request.POST, instance=check_out)
        if form.is_valid():
            check_out = form.save(commit=False)
            if not check_out.is_completed:
                check_out.is_completed = True
                check_out.completed_at = timezone.now()
                check_out.completed_by = request.user
            check_out.save()
            messages.success(request, 'Đã cập nhật biên bản trả phòng thành công.')
            return redirect('registration:check_out_detail', check_out_id=check_out.id)
    else:
        form = CheckOutForm(instance=check_out)

    context = {
        'form': form,
        'check_out': check_out,
        'page_title': 'Chi tiết biên bản trả phòng',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Biên bản trả phòng', 'url': reverse('registration:check_out_list')},
            {'title': f'Biên bản #{check_out.id}', 'url': None}
        ]
    }
    return render(request, 'registration/admin/check_out_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def period_delete_view(request, period_id):
    """Xóa kỳ đăng ký"""
    period = get_object_or_404(RegistrationPeriod, pk=period_id)
    
    if request.method == 'POST':
        if period.registrations.exists():
            messages.error(request, 'Không thể xóa kỳ đăng ký này vì đã có sinh viên đăng ký.')
            return redirect('registration:period_list')
            
        period.delete()
        messages.success(request, 'Đã xóa kỳ đăng ký thành công.')
        return redirect('registration:period_list')
        
    context = {
        'period': period,
        'page_title': 'Xóa kỳ đăng ký',
        'breadcrumbs': [
            {'title': 'Quản lý đăng ký', 'url': '#'},
            {'title': 'Danh sách kỳ đăng ký', 'url': reverse('registration:period_list')},
            {'title': 'Xóa kỳ đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/admin/period_delete.html', context)


@login_required
def application_cancel_view(request, application_id):
    """Hủy đơn đăng ký phòng"""
    registration = get_object_or_404(RoomRegistration, pk=application_id, user=request.user)
    
    if registration.status not in ['pending']:
        messages.error(request, 'Chỉ có thể hủy đơn đăng ký đang chờ xét duyệt.')
        return redirect('registration:my_applications')
    
    if request.method == 'POST':
        registration.status = 'cancelled'
        registration.cancelled_at = timezone.now()
        registration.save(update_fields=['status', 'cancelled_at'])
        
        messages.success(request, 'Đã hủy đơn đăng ký thành công.')
        return redirect('registration:my_applications')
    
    context = {
        'registration': registration,
        'page_title': 'Hủy đơn đăng ký',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Đơn đăng ký của tôi', 'url': reverse('registration:my_applications')},
            {'title': 'Hủy đơn đăng ký', 'url': None}
        ]
    }
    return render(request, 'registration/admin/application_cancel.html', context)
