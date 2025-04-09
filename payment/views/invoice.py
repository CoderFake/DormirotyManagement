from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, F
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import datetime
import csv
import uuid

from accounts.views import is_admin_or_staff
from accounts.models import User
from dormitory.models import Room
from registration.models import Contract
from payment.models import Invoice, InvoiceItem, Payment, FeeType
from payment.forms import InvoiceForm, InvoiceItemForm, PaymentForm


@login_required
def payment_history_view(request):
    payments = Payment.objects.filter(user=request.user).select_related('invoice').order_by('-payment_date')

    context = {
        'payments': payments,
        'page_title': 'Lịch sử thanh toán',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Lịch sử thanh toán', 'url': None}
        ]
    }

    return render(request, 'payment/payment_history.html', context)


@login_required
def pay_invoice_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)

    if invoice.status not in ['pending', 'partially_paid', 'overdue']:
        messages.error(request, 'Hóa đơn này không trong trạng thái có thể thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    amount_to_pay = invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.error(request, 'Hóa đơn này đã được thanh toán đầy đủ.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    return redirect('payment:payment_methods', invoice_id=invoice.id)


@login_required
def my_invoices_view(request):

    invoices = Invoice.objects.filter(user=request.user).select_related('room').order_by('-issue_date')

    total_invoices = invoices.count()
    pending_invoices = invoices.filter(status__in=['pending', 'partially_paid', 'overdue']).count()
    total_unpaid = invoices.filter(status__in=['pending', 'partially_paid', 'overdue']).aggregate(
        total=Sum(F('total_amount') - F('paid_amount')))['total'] or 0

    context = {
        'invoices': invoices,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'total_unpaid': total_unpaid,
        'page_title': 'Hóa đơn của tôi',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn của tôi', 'url': None}
        ]
    }

    return render(request, 'payment/my_invoices.html', context)

@login_required
def invoice_list_view(request):
    """Danh sách hóa đơn"""
    # Kiểm tra quyền truy cập
    is_admin = request.user.user_type in ['admin', 'staff']
    
    # Lấy danh sách hóa đơn
    if is_admin:
        invoices = Invoice.objects.all().select_related('user', 'room')
    else:
        invoices = Invoice.objects.filter(user=request.user).select_related('room')
    
    # Lọc theo trạng thái
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    # Lọc theo người dùng (chỉ admin)
    if is_admin:
        user_id = request.GET.get('user')
        if user_id:
            invoices = invoices.filter(user_id=user_id)
    
    # Lọc theo phòng
    room_id = request.GET.get('room')
    if room_id:
        invoices = invoices.filter(room_id=room_id)
    
    # Tìm kiếm
    search_query = request.GET.get('q')
    if search_query:
        if is_admin:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search_query) |
                Q(user__full_name__icontains=search_query) |
                Q(user__student_id__icontains=search_query)
            )
        else:
            invoices = invoices.filter(
                Q(invoice_number__icontains=search_query)
            )
    
    # Sắp xếp
    invoices = invoices.order_by('-issue_date')
    
    # Phân trang
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page', 1)
    invoices_page = paginator.get_page(page_number)
    
    context = {
        'invoices': invoices_page,
        'status': status,
        'search_query': search_query,
        'is_admin': is_admin,
        'page_title': 'Danh sách hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': None}
        ]
    }
    
    # Thêm dữ liệu cho admin
    if is_admin:
        context['users'] = User.objects.filter(user_type='student')
        context['rooms'] = Room.objects.filter(is_active=True)
    
    return render(request, 'payment/invoice_list.html', context)


@login_required
def invoice_detail_view(request, invoice_id):
    """Chi tiết hóa đơn"""
    # Kiểm tra quyền truy cập
    is_admin = request.user.user_type in ['admin', 'staff']
    
    # Lấy hóa đơn
    if is_admin:
        invoice = get_object_or_404(Invoice, pk=invoice_id)
    else:
        invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    # Lấy các mục hóa đơn
    items = invoice.items.all()
    
    # Lấy các thanh toán
    payments = invoice.payments.all().order_by('-payment_date')
    
    context = {
        'invoice': invoice,
        'items': items,
        'payments': payments,
        'is_admin': is_admin,
        'page_title': f'Chi tiết hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_create_view(request):
    """Tạo hóa đơn mới"""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.save()
            
            messages.success(request, 'Đã tạo hóa đơn mới thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm()
    
    context = {
        'form': form,
        'page_title': 'Tạo hóa đơn mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_edit_view(request, invoice_id):
    """Chỉnh sửa hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            
            messages.success(request, 'Đã cập nhật hóa đơn thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm(instance=invoice)
    
    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Chỉnh sửa hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_delete_view(request, invoice_id):
    """Xóa hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    if request.method == 'POST':
        invoice.delete()
        
        messages.success(request, 'Đã xóa hóa đơn thành công.')
        return redirect('payment:invoice_list')
    
    context = {
        'invoice': invoice,
        'page_title': f'Xóa hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Xóa', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_item_create_view(request, invoice_id):
    """Thêm mục hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    if request.method == 'POST':
        form = InvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.invoice = invoice
            item.save()
            
            messages.success(request, 'Đã thêm mục hóa đơn thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceItemForm()
    
    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Thêm mục hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Thêm mục', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_item_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_item_edit_view(request, item_id):
    """Chỉnh sửa mục hóa đơn"""
    item = get_object_or_404(InvoiceItem, pk=item_id)
    invoice = item.invoice
    
    if request.method == 'POST':
        form = InvoiceItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            
            messages.success(request, 'Đã cập nhật mục hóa đơn thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceItemForm(instance=item)
    
    context = {
        'form': form,
        'item': item,
        'invoice': invoice,
        'page_title': f'Chỉnh sửa mục hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice.id])},
            {'title': 'Chỉnh sửa mục', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_item_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_item_delete_view(request, item_id):
    """Xóa mục hóa đơn"""
    item = get_object_or_404(InvoiceItem, pk=item_id)
    invoice = item.invoice
    
    if request.method == 'POST':
        item.delete()
        
        messages.success(request, 'Đã xóa mục hóa đơn thành công.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)
    
    context = {
        'item': item,
        'invoice': invoice,
        'page_title': f'Xóa mục hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice.id])},
            {'title': 'Xóa mục', 'url': None}
        ]
    }
    
    return render(request, 'payment/invoice_item_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def record_payment_view(request, invoice_id):
    """Ghi nhận thanh toán"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.user = invoice.user
            payment.save()
            
            # Cập nhật hóa đơn
            invoice.record_payment(payment.amount, payment.payment_method, payment.transaction_id)
            
            messages.success(request, 'Đã ghi nhận thanh toán thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = PaymentForm(initial={
            'amount': invoice.get_remaining_amount(),
            'payment_date': timezone.now()
        })
    
    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Ghi nhận thanh toán hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Ghi nhận thanh toán', 'url': None}
        ]
    }
    
    return render(request, 'payment/record_payment.html', context)


@login_required
def payment_methods_view(request, invoice_id):
    """Chọn phương thức thanh toán"""
    # Kiểm tra quyền truy cập
    is_admin = request.user.user_type in ['admin', 'staff']
    
    # Lấy hóa đơn
    if is_admin:
        invoice = get_object_or_404(Invoice, pk=invoice_id)
    else:
        invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    # Kiểm tra trạng thái hóa đơn
    if invoice.status not in ['pending', 'partially_paid', 'overdue']:
        messages.error(request, 'Hóa đơn này không trong trạng thái có thể thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)
    
    # Tính số tiền cần thanh toán
    amount_to_pay = invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.error(request, 'Hóa đơn này đã được thanh toán đầy đủ.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)
    
    context = {
        'invoice': invoice,
        'amount_to_pay': amount_to_pay,
        'page_title': f'Chọn phương thức thanh toán hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Thanh toán', 'url': None}
        ]
    }
    
    return render(request, 'payment/payment_methods.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def generate_monthly_invoices(request):
    """Tạo hóa đơn hàng tháng"""
    if request.method == 'POST':
        month = int(request.POST.get('month', timezone.now().month))
        year = int(request.POST.get('year', timezone.now().year))
        
        # Lấy danh sách hợp đồng đang hoạt động
        active_contracts = Contract.objects.filter(
            status='active',
            start_date__lte=datetime.date(year, month, 1),
            end_date__gte=datetime.date(year, month, 1)
        )
        
        # Tạo hóa đơn cho từng hợp đồng
        created_count = 0
        for contract in active_contracts:
            # Kiểm tra xem đã có hóa đơn cho tháng này chưa
            existing_invoice = Invoice.objects.filter(
                contract=contract,
                month=month,
                year=year
            ).exists()
            
            if not existing_invoice:
                # Tạo hóa đơn mới
                due_date = datetime.date(year, month, 15)  # Ngày 15 hàng tháng
                if due_date < timezone.now().date():
                    due_date = timezone.now().date() + datetime.timedelta(days=7)
                
                invoice = Invoice.objects.create(
                    user=contract.user,
                    contract=contract,
                    room=contract.room,
                    issue_date=timezone.now().date(),
                    due_date=due_date,
                    month=month,
                    year=year,
                    status='pending'
                )
                
                # Thêm mục tiền phòng
                room_fee_type, _ = FeeType.objects.get_or_create(
                    code='ROOM_FEE',
                    defaults={
                        'name': 'Tiền phòng',
                        'description': 'Phí thuê phòng hàng tháng',
                        'is_recurring': True
                    }
                )
                
                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=room_fee_type,
                    description=f'Tiền phòng tháng {month}/{year}',
                    quantity=1,
                    unit_price=contract.monthly_fee,
                    amount=contract.monthly_fee
                )
                
                created_count += 1
        
        messages.success(request, f'Đã tạo {created_count} hóa đơn tiền phòng cho tháng {month}/{year}.')
        return redirect('payment:invoice_list')
    
    context = {
        'page_title': 'Tạo hóa đơn hàng tháng',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo hóa đơn hàng tháng', 'url': None}
        ]
    }
    
    return render(request, 'payment/generate_monthly_invoices.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def generate_utility_invoices(request):
    """Tạo hóa đơn tiện ích (điện, nước)"""
    if request.method == 'POST':
        month = int(request.POST.get('month', timezone.now().month))
        year = int(request.POST.get('year', timezone.now().year))
        utility_type = request.POST.get('utility_type')
        
        if utility_type not in ['electricity', 'water', 'both']:
            messages.error(request, 'Loại tiện ích không hợp lệ.')
            return redirect('payment:generate_utility_invoices')
        
        # Lấy danh sách phòng có người ở
        occupied_rooms = Room.objects.filter(
            status__in=['partially_occupied', 'fully_occupied']
        )
        
        # Tạo hóa đơn cho từng phòng
        created_count = 0
        
        for room in occupied_rooms:
            # Lấy danh sách hợp đồng đang hoạt động trong phòng
            active_contracts = Contract.objects.filter(
                room=room,
                status='active',
                start_date__lte=datetime.date(year, month, 1),
                end_date__gte=datetime.date(year, month, 1)
            )
            
            if not active_contracts.exists():
                continue
            
            # Tính số người trong phòng
            occupants_count = active_contracts.count()
            
            # Xử lý hóa đơn điện
            if utility_type in ['electricity', 'both']:
                from payment.models import ElectricityReading
                
                # Lấy chỉ số điện của tháng này và tháng trước
                current_reading = ElectricityReading.objects.filter(
                    room=room,
                    month=month,
                    year=year
                ).first()
                
                if current_reading and not current_reading.is_billed:
                    # Tạo hóa đơn điện
                    for contract in active_contracts:
                        # Kiểm tra xem đã có hóa đơn điện cho tháng này chưa
                        existing_invoice = Invoice.objects.filter(
                            contract=contract,
                            month=month,
                            year=year,
                            items__fee_type__code='ELECTRICITY'
                        ).exists()
                        
                        if not existing_invoice:
                            # Tìm hoặc tạo hóa đơn cho tháng này
                            invoice = Invoice.objects.filter(
                                contract=contract,
                                month=month,
                                year=year
                            ).first()
                            
                            if not invoice:
                                due_date = datetime.date(year, month, 15)  # Ngày 15 hàng tháng
                                if due_date < timezone.now().date():
                                    due_date = timezone.now().date() + datetime.timedelta(days=7)
                                
                                invoice = Invoice.objects.create(
                                    user=contract.user,
                                    contract=contract,
                                    room=room,
                                    issue_date=timezone.now().date(),
                                    due_date=due_date,
                                    month=month,
                                    year=year,
                                    status='pending'
                                )
                            
                            # Thêm mục tiền điện
                            electricity_fee_type, _ = FeeType.objects.get_or_create(
                                code='ELECTRICITY',
                                defaults={
                                    'name': 'Tiền điện',
                                    'description': 'Phí sử dụng điện hàng tháng',
                                    'is_recurring': True
                                }
                            )
                            
                            # Tính tiền điện cho mỗi người
                            per_person_amount = current_reading.amount / occupants_count
                            
                            InvoiceItem.objects.create(
                                invoice=invoice,
                                fee_type=electricity_fee_type,
                                description=f'Tiền điện tháng {month}/{year} ({current_reading.get_usage()} kWh)',
                                quantity=1,
                                unit_price=per_person_amount,
                                amount=per_person_amount
                            )
                            
                            created_count += 1
                    
                    # Đánh dấu đã lập hóa đơn
                    current_reading.is_billed = True
                    current_reading.save()
            
            # Xử lý hóa đơn nước
            if utility_type in ['water', 'both']:
                from payment.models import WaterReading
                
                # Lấy chỉ số nước của tháng này và tháng trước
                current_reading = WaterReading.objects.filter(
                    room=room,
                    month=month,
                    year=year
                ).first()
                
                if current_reading and not current_reading.is_billed:
                    # Tạo hóa đơn nước
                    for contract in active_contracts:
                        # Kiểm tra xem đã có hóa đơn nước cho tháng này chưa
                        existing_invoice = Invoice.objects.filter(
                            contract=contract,
                            month=month,
                            year=year,
                            items__fee_type__code='WATER'
                        ).exists()
                        
                        if not existing_invoice:
                            # Tìm hoặc tạo hóa đơn cho tháng này
                            invoice = Invoice.objects.filter(
                                contract=contract,
                                month=month,
                                year=year
                            ).first()
                            
                            if not invoice:
                                due_date = datetime.date(year, month, 15)  # Ngày 15 hàng tháng
                                if due_date < timezone.now().date():
                                    due_date = timezone.now().date() + datetime.timedelta(days=7)
                                
                                invoice = Invoice.objects.create(
                                    user=contract.user,
                                    contract=contract,
                                    room=room,
                                    issue_date=timezone.now().date(),
                                    due_date=due_date,
                                    month=month,
                                    year=year,
                                    status='pending'
                                )
                            
                            # Thêm mục tiền nước
                            water_fee_type, _ = FeeType.objects.get_or_create(
                                code='WATER',
                                defaults={
                                    'name': 'Tiền nước',
                                    'description': 'Phí sử dụng nước hàng tháng',
                                    'is_recurring': True
                                }
                            )
                            
                            # Tính tiền nước cho mỗi người
                            per_person_amount = current_reading.amount / occupants_count
                            
                            InvoiceItem.objects.create(
                                invoice=invoice,
                                fee_type=water_fee_type,
                                description=f'Tiền nước tháng {month}/{year} ({current_reading.get_usage()} m³)',
                                quantity=1,
                                unit_price=per_person_amount,
                                amount=per_person_amount
                            )
                            
                            created_count += 1
                    
                    # Đánh dấu đã lập hóa đơn
                    current_reading.is_billed = True
                    current_reading.save()
        
        utility_name = 'điện và nước' if utility_type == 'both' else ('điện' if utility_type == 'electricity' else 'nước')
        messages.success(request, f'Đã tạo {created_count} hóa đơn tiền {utility_name} cho tháng {month}/{year}.')
        return redirect('payment:invoice_list')
    
    context = {
        'page_title': 'Tạo hóa đơn tiện ích',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo hóa đơn tiện ích', 'url': None}
        ]
    }
    
    return render(request, 'payment/generate_utility_invoices.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def export_invoices_csv(request):
    """Xuất danh sách hóa đơn ra file CSV"""
    # Lấy danh sách hóa đơn
    invoices = Invoice.objects.all().select_related('user', 'room')
    
    # Lọc theo trạng thái
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    # Lọc theo người dùng
    user_id = request.GET.get('user')
    if user_id:
        invoices = invoices.filter(user_id=user_id)
    
    # Lọc theo phòng
    room_id = request.GET.get('room')
    if room_id:
        invoices = invoices.filter(room_id=room_id)
    
    # Tìm kiếm
    search_query = request.GET.get('q')
    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(user__full_name__icontains=search_query) |
            Q(user__student_id__icontains=search_query)
        )
    
    # Sắp xếp
    invoices = invoices.order_by('-issue_date')
    
    # Tạo response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    
    # Tạo writer
    writer = csv.writer(response)
    writer.writerow([
        'Số hóa đơn',
        'Sinh viên',
        'MSSV',
        'Phòng',
        'Ngày lập',
        'Ngày đến hạn',
        'Tổng tiền',
        'Đã thanh toán',
        'Còn lại',
        'Trạng thái'
    ])
    
    # Ghi dữ liệu
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.user.full_name,
            invoice.user.student_id if hasattr(invoice.user, 'student_id') else '',
            f"{invoice.room.building.name} - {invoice.room.room_number}" if invoice.room else '',
            invoice.issue_date.strftime('%Y-%m-%d'),
            invoice.due_date.strftime('%Y-%m-%d'),
            invoice.total_amount,
            invoice.paid_amount,
            invoice.get_remaining_amount(),
            invoice.get_status_display()
        ])
    
    return response


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_item_create_ajax(request, invoice_id):
    """Tạo mục hóa đơn qua AJAX"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == 'POST':
        try:
            fee_type_id = request.POST.get('fee_type')
            description = request.POST.get('description')
            quantity = int(request.POST.get('quantity', 1))
            unit_price = float(request.POST.get('unit_price', 0))

            fee_type = get_object_or_404(FeeType, pk=fee_type_id)

            # Tạo mục hóa đơn mới
            item = InvoiceItem.objects.create(
                invoice=invoice,
                fee_type=fee_type,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=quantity * unit_price
            )
            invoice.total_amount = sum(item.amount for item in invoice.items.all())
            invoice.save()

            return JsonResponse({
                'success': True,
                'item_id': str(item.id),
                'message': 'Đã thêm mục hóa đơn thành công.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Lỗi: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'message': 'Phương thức không hợp lệ.'
    })
