from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.urls import reverse
import datetime

from registration.models import Contract
from payment.models import Invoice, InvoiceItem, FeeType, Payment


@login_required
def deposit_payment_view(request, contract_id):
    """Thanh toán tiền đặt cọc"""
    contract = get_object_or_404(Contract, pk=contract_id, user=request.user)
    
    if contract.status != 'draft':
        messages.error(request, 'Hợp đồng này không trong trạng thái chờ thanh toán tiền cọc.')
        return redirect('registration:contract_detail', contract_id=contract.id)

    # Tạo hóa đơn tiền cọc nếu chưa có
    invoice = Invoice.objects.filter(contract=contract, status='pending').first()
    if not invoice:
        invoice = Invoice.objects.create(
            user=request.user,
            contract=contract,
            room=contract.room,
            due_date=timezone.now().date() + datetime.timedelta(days=7),
            total_amount=contract.deposit_amount,
            status='pending'
        )
        
        fee_type, _ = FeeType.objects.get_or_create(
            code='DEPOSIT',
            defaults={
                'name': 'Tiền đặt cọc',
                'description': 'Tiền đặt cọc ký túc xá',
                'is_recurring': False
            }
        )
        
        InvoiceItem.objects.create(
            invoice=invoice,
            fee_type=fee_type,
            description='Tiền đặt cọc ký túc xá',
            quantity=1,
            unit_price=contract.deposit_amount,
            amount=contract.deposit_amount
        )

    # Hiển thị trang chọn phương thức thanh toán
    context = {
        'invoice': invoice,
        'contract': contract,
        'page_title': 'Thanh toán tiền đặt cọc',
        'breadcrumbs': [
            {'title': 'Đăng ký phòng', 'url': '#'},
            {'title': 'Hợp đồng của tôi', 'url': reverse('registration:my_contracts')},
            {'title': f'Hợp đồng #{contract.contract_number}', 'url': reverse('registration:contract_detail', args=[contract_id])},
            {'title': 'Thanh toán tiền đặt cọc', 'url': None}
        ]
    }
    
    return render(request, 'payment/deposit_payment.html', context)


@login_required
def payment_methods_view(request, invoice_id):
    """Chọn phương thức thanh toán"""
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
