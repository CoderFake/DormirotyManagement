from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import hmac
import hashlib
import urllib.parse
import datetime
import random

from accounts.models import User
from dormitory.models import Room
from registration.models import Contract
from .models import (
    FeeType, Invoice, InvoiceItem, Payment,
    ElectricityReading, WaterReading, VNPayTransaction
)
from .forms import (
    FeeTypeForm, InvoiceForm, InvoiceItemForm, PaymentForm,
    ElectricityReadingForm, WaterReadingForm, VNPayPaymentForm
)


def is_admin(user):
    return user.is_authenticated and user.user_type == 'admin'


def is_admin_or_staff(user):
    return user.is_authenticated and user.user_type in ['admin', 'staff']


# ====== Views cho sinh viên ======

@login_required
def my_invoices_view(request):
    """Xem danh sách hóa đơn của sinh viên"""
    invoices = Invoice.objects.filter(user=request.user).order_by('-issue_date')

    total_invoices = invoices.count()
    pending_invoices = invoices.filter(status__in=['pending', 'overdue', 'partially_paid']).count()
    total_unpaid = sum(invoice.get_remaining_amount() for invoice in invoices.filter(
        status__in=['pending', 'overdue', 'partially_paid']
    ))

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
def invoice_detail_view(request, invoice_id):
    """Xem chi tiết hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if not (invoice.user == request.user or is_admin_or_staff(request.user)):
        messages.error(request, 'Bạn không có quyền xem hóa đơn này.')
        return redirect('payment:my_invoices')

    items = InvoiceItem.objects.filter(invoice=invoice)
    payments = Payment.objects.filter(invoice=invoice).order_by('-payment_date')

    context = {
        'invoice': invoice,
        'items': items,
        'payments': payments,
        'page_title': f'Chi tiết hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn của tôi', 'url': reverse('payment:my_invoices')},
            {'title': f'#{invoice.invoice_number}', 'url': None}
        ]
    }
    return render(request, 'payment/invoice_detail.html', context)


@login_required
def payment_methods_view(request):
    """Hiển thị các phương thức thanh toán"""
    unpaid_invoices = Invoice.objects.filter(
        user=request.user,
        status__in=['pending', 'overdue', 'partially_paid']
    ).order_by('due_date')

    total_amount = sum(invoice.get_remaining_amount() for invoice in unpaid_invoices)

    form = VNPayPaymentForm()

    context = {
        'unpaid_invoices': unpaid_invoices,
        'total_amount': total_amount,
        'form': form,
        'page_title': 'Phương thức thanh toán',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Phương thức thanh toán', 'url': None}
        ]
    }
    return render(request, 'payment/payment_methods.html', context)


@login_required
def pay_invoice_view(request, invoice_id):
    """Thanh toán một hóa đơn cụ thể"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if invoice.user != request.user:
        messages.error(request, 'Bạn không có quyền thanh toán hóa đơn này.')
        return redirect('payment:my_invoices')

    if invoice.status not in ['pending', 'overdue', 'partially_paid']:
        messages.error(request, 'Hóa đơn này không cần thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice_id)

    initial_amount = invoice.get_remaining_amount()
    form = VNPayPaymentForm(
        initial={'amount': initial_amount, 'order_info': f'Thanh toán hóa đơn #{invoice.invoice_number}'})

    if request.method == 'POST':
        form = VNPayPaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            order_info = form.cleaned_data['order_info'] or f'Thanh toán hóa đơn #{invoice.invoice_number}'
            txn_ref = f"INV{invoice.id.hex[:8]}{int(timezone.now().timestamp())}"

            transaction = VNPayTransaction.objects.create(
                user=request.user,
                amount=amount,
                order_info=order_info,
                txn_ref=txn_ref,
                transaction_status='pending'
            )

            # Tạo URL thanh toán VNPay
            vnpay_url = create_vnpay_url(transaction)

            return redirect(vnpay_url)

    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Thanh toán hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn của tôi', 'url': reverse('payment:my_invoices')},
            {'title': f'#{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Thanh toán', 'url': None}
        ]
    }
    return render(request, 'payment/pay_invoice.html', context)


@login_required
def payment_history_view(request):
    """Lịch sử thanh toán"""
    payments = Payment.objects.filter(user=request.user).order_by('-payment_date')

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
def create_payment_view(request):
    """Tạo một giao dịch thanh toán mới"""
    if request.method == 'POST':
        form = VNPayPaymentForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            order_info = form.cleaned_data['order_info'] or 'Thanh toán ký túc xá'

            txn_ref = f"PAY{request.user.id.hex[:8]}{int(timezone.now().timestamp())}"

            transaction = VNPayTransaction.objects.create(
                user=request.user,
                amount=amount,
                order_info=order_info,
                txn_ref=txn_ref,
                transaction_status='pending'
            )
            vnpay_url = create_vnpay_url(transaction)

            return redirect(vnpay_url)
    else:
        form = VNPayPaymentForm()

    context = {
        'form': form,
        'page_title': 'Tạo giao dịch thanh toán',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Tạo giao dịch', 'url': None}
        ]
    }
    return render(request, 'payment/create_payment.html', context)


@csrf_exempt
def vnpay_return_view(request):
    """Xử lý kết quả trả về từ VNPay"""
    vnp_params = request.GET.copy()
    vnp_txn_ref = vnp_params.get('vnp_TxnRef')
    vnp_response_code = vnp_params.get('vnp_ResponseCode')

    try:
        transaction = VNPayTransaction.objects.get(txn_ref=vnp_txn_ref)
    except VNPayTransaction.DoesNotExist:
        messages.error(request, 'Không tìm thấy thông tin giao dịch.')
        return redirect('payment:payment_methods')

    vnp_secure_hash = vnp_params.pop('vnp_SecureHash', None)

    if not vnp_secure_hash:
        transaction.transaction_status = 'failed'
        transaction.response_code = '99'
        transaction.response_message = 'Thiếu thông tin xác thực'
        transaction.save()

        messages.error(request, 'Thiếu thông tin xác thực giao dịch.')
        return redirect('payment:payment_methods')

    if vnp_response_code == '00':
        transaction.transaction_status = 'success'
        transaction.response_code = vnp_response_code
        transaction.response_message = 'Giao dịch thành công'
        transaction.transaction_date = timezone.now()
        transaction.bank_code = vnp_params.get('vnp_BankCode')
        transaction.card_type = vnp_params.get('vnp_CardType')
        transaction.save()

        if vnp_txn_ref.startswith('INV'):
            invoice_id = vnp_txn_ref[3:11]
            try:
                invoice = Invoice.objects.get(id__startswith=invoice_id)
                payment = Payment.objects.create(
                    invoice=invoice,
                    user=transaction.user,
                    amount=transaction.amount,
                    payment_method='vnpay',
                    transaction_id=vnp_txn_ref,
                    status='completed'
                )

                invoice.paid_amount += transaction.amount
                invoice.save()

                transaction.payment = payment
                transaction.save()
            except Invoice.DoesNotExist:
                pass
        else:
            unpaid_invoices = Invoice.objects.filter(
                user=transaction.user,
                status__in=['pending', 'overdue', 'partially_paid']
            ).order_by('due_date')

            remaining_amount = transaction.amount
            for invoice in unpaid_invoices:
                if remaining_amount <= 0:
                    break

                invoice_remaining = invoice.get_remaining_amount()
                payment_amount = min(remaining_amount, invoice_remaining)

                if payment_amount > 0:
                    payment = Payment.objects.create(
                        invoice=invoice,
                        user=transaction.user,
                        amount=payment_amount,
                        payment_method='vnpay',
                        transaction_id=vnp_txn_ref,
                        status='completed'
                    )

                    invoice.paid_amount += payment_amount
                    invoice.save()

                    if not transaction.payment:
                        transaction.payment = payment
                        transaction.save()

                    remaining_amount -= payment_amount

        messages.success(request, 'Thanh toán thành công!')
        context = {
            'payment_success': True,
            'transaction_id': vnp_txn_ref,
            'amount': transaction.amount,
            'transaction_date': transaction.transaction_date,
            'page_title': 'Kết quả thanh toán',
            'breadcrumbs': [
                {'title': 'Thanh toán', 'url': '#'},
                {'title': 'Kết quả', 'url': None}
            ]
        }
    else:
        transaction.transaction_status = 'failed'
        transaction.response_code = vnp_response_code
        transaction.response_message = 'Giao dịch thất bại'
        transaction.transaction_date = timezone.now()
        transaction.save()

        messages.error(request, 'Thanh toán không thành công. Vui lòng thử lại sau.')
        context = {
            'payment_success': False,
            'transaction_id': vnp_txn_ref,
            'error_code': vnp_response_code,
            'error_message': 'Giao dịch không thành công',
            'transaction_date': transaction.transaction_date,
            'page_title': 'Kết quả thanh toán',
            'breadcrumbs': [
                {'title': 'Thanh toán', 'url': '#'},
                {'title': 'Kết quả', 'url': None}
            ]
        }

    return render(request, 'payment/vnpay_return.html', context)


@csrf_exempt
def vnpay_ipn_view(request):
    """Xử lý IPN (Instant Payment Notification) từ VNPay"""
    vnp_params = request.GET.copy()
    vnp_txn_ref = vnp_params.get('vnp_TxnRef')
    vnp_response_code = vnp_params.get('vnp_ResponseCode')

    try:
        transaction = VNPayTransaction.objects.get(txn_ref=vnp_txn_ref)
    except VNPayTransaction.DoesNotExist:
        return HttpResponse('Không tìm thấy giao dịch', status=404)

    vnp_secure_hash = vnp_params.pop('vnp_SecureHash', None)

    if not vnp_secure_hash:
        return HttpResponse('Thiếu thông tin xác thực', status=400)

    if vnp_response_code == '00':
        transaction.transaction_status = 'success'
        transaction.response_code = vnp_response_code
        transaction.response_message = 'Giao dịch thành công'
        transaction.transaction_date = timezone.now()
        transaction.bank_code = vnp_params.get('vnp_BankCode')
        transaction.card_type = vnp_params.get('vnp_CardType')
        transaction.save()

        return HttpResponse('OK', status=200)
    else:
        transaction.transaction_status = 'failed'
        transaction.response_code = vnp_response_code
        transaction.response_message = 'Giao dịch thất bại'
        transaction.transaction_date = timezone.now()
        transaction.save()

        return HttpResponse('Giao dịch thất bại', status=200)


# ====== Views cho Admin ======

@login_required
@user_passes_test(is_admin_or_staff)
def fee_type_list_view(request):
    """Danh sách loại phí"""
    fee_types = FeeType.objects.all().order_by('name')

    context = {
        'fee_types': fee_types,
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
            messages.success(request, 'Tạo loại phí mới thành công.')
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
            messages.success(request, 'Cập nhật loại phí thành công.')
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
    return render(request, 'payment/admin/fee_type_form.html', context)


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
    return render(request, 'payment/admin/fee_type_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_list_view(request):
    """Danh sách tất cả hóa đơn"""
    invoices = Invoice.objects.all().order_by('-issue_date')

    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)

    user_id = request.GET.get('user')
    if user_id:
        invoices = invoices.filter(user_id=user_id)

    room_id = request.GET.get('room')
    if room_id:
        invoices = invoices.filter(room_id=room_id)

    context = {
        'invoices': invoices,
        'page_title': 'Danh sách hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': None}
        ]
    }
    return render(request, 'payment/admin/invoice_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_create_view(request):
    """Tạo hóa đơn mới"""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            invoice = form.save(commit=False)
            invoice.issue_date = timezone.now().date()
            invoice.save()

            messages.success(request, f'Tạo hóa đơn mới thành công. Số hóa đơn: {invoice.invoice_number}')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceForm()
        form.fields['due_date'].initial = timezone.now().date() + timezone.timedelta(days=15)
        form.fields['month'].initial = timezone.now().month
        form.fields['year'].initial = timezone.now().year

    context = {
        'form': form,
        'page_title': 'Tạo hóa đơn mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'payment/admin/invoice_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_edit_view(request, invoice_id):
    """Chỉnh sửa hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật hóa đơn thành công.')
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
            {'title': f'#{invoice.invoice_number}', 'url': reverse('payment:invoice_detail', args=[invoice_id])},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'payment/admin/invoice_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def invoice_delete_view(request, invoice_id):
    """Xóa hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == 'POST':
        invoice_number = invoice.invoice_number
        invoice.delete()
        messages.success(request, f'Đã xóa hóa đơn: {invoice_number}')
        return redirect('payment:invoice_list')

    context = {
        'invoice': invoice,
        'page_title': f'Xóa hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'payment/admin/invoice_delete.html', context)


# ====== Hàm hỗ trợ ======

def create_vnpay_url(transaction):
    """Tạo URL thanh toán VNPay"""
    vnp_tmn_code = settings.VNPAY_TMN_CODE
    vnp_hash_secret = settings.VNPAY_HASH_SECRET_KEY
    vnp_url = settings.VNPAY_PAYMENT_URL
    vnp_return_url = settings.VNPAY_RETURN_URL

    vnp_txn_ref = transaction.txn_ref
    vnp_order_info = transaction.order_info
    vnp_amount = int(transaction.amount) * 100
    vnp_locale = 'vn'
    vnp_currency = 'VND'
    vnp_ip_addr = '127.0.0.1'
    vnp_create_date = timezone.now().strftime('%Y%m%d%H%M%S')

    vnp_params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': vnp_tmn_code,
        'vnp_Amount': vnp_amount,
        'vnp_CurrCode': vnp_currency,
        'vnp_TxnRef': vnp_txn_ref,
        'vnp_OrderInfo': vnp_order_info,
        'vnp_OrderType': 'billpayment',
        'vnp_Locale': vnp_locale,
        'vnp_ReturnUrl': vnp_return_url,
        'vnp_IpAddr': vnp_ip_addr,
        'vnp_CreateDate': vnp_create_date
    }

    sorted_params = sorted(vnp_params.items())

    hash_data = '&'.join([f"{k}={v}" for k, v in sorted_params])
    vnp_secure_hash = hmac.new(
        vnp_hash_secret.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

    vnp_params['vnp_SecureHash'] = vnp_secure_hash

    query_string = urllib.parse.urlencode(vnp_params)
    return f"{vnp_url}?{query_string}"