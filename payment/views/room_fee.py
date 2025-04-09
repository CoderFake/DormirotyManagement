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
from registration.models import Contract
from payment.models import Invoice, InvoiceItem, FeeType


@login_required
@user_passes_test(is_admin_or_staff)
def generate_room_fee_invoices(request):
    """Tạo hóa đơn tiền phòng hàng tháng"""
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
                year=year,
                items__fee_type__code='ROOM_FEE'
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
        'current_month': timezone.now().month,
        'current_year': timezone.now().year,
        'page_title': 'Tạo hóa đơn tiền phòng hàng tháng',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo hóa đơn tiền phòng', 'url': None}
        ]
    }
    
    return render(request, 'payment/generate_room_fee_invoices.html', context)


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
        from dormitory.models import Room
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
                from payment.payment_models import ElectricityReading
                
                # Lấy chỉ số điện của tháng này
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
                    current_reading.invoice = invoice
                    current_reading.save()
            
            # Xử lý hóa đơn nước
            if utility_type in ['water', 'both']:
                from payment.payment_models import WaterReading
                
                # Lấy chỉ số nước của tháng này
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
                    current_reading.invoice = invoice
                    current_reading.save()
        
        utility_name = 'điện và nước' if utility_type == 'both' else ('điện' if utility_type == 'electricity' else 'nước')
        messages.success(request, f'Đã tạo {created_count} hóa đơn tiền {utility_name} cho tháng {month}/{year}.')
        return redirect('payment:invoice_list')
    
    context = {
        'current_month': timezone.now().month,
        'current_year': timezone.now().year,
        'page_title': 'Tạo hóa đơn tiện ích',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo hóa đơn tiện ích', 'url': None}
        ]
    }
    
    return render(request, 'payment/generate_utility_invoices.html', context)
