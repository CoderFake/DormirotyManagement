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
@user_passes_test(is_admin_or_staff)
def invoice_add_item_view(request, invoice_id):
    """Thêm mục vào hóa đơn"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == 'POST':
        form = InvoiceItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.invoice = invoice
            item.save()

            messages.success(request, 'Thêm mục vào hóa đơn thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceItemForm()

    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Thêm mục vào hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}',
             'url': reverse('payment:invoice_detail', kwargs={'invoice_id': invoice.id})},
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
            messages.success(request, 'Cập nhật mục hóa đơn thành công.')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        form = InvoiceItemForm(instance=item)

    context = {
        'form': form,
        'item': item,
        'invoice': invoice,
        'page_title': 'Chỉnh sửa mục hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}',
             'url': reverse('payment:invoice_detail', kwargs={'invoice_id': invoice.id})},
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
        messages.success(request, 'Đã xóa mục hóa đơn.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    context = {
        'item': item,
        'invoice': invoice,
        'page_title': 'Xóa mục hóa đơn',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}',
             'url': reverse('payment:invoice_detail', kwargs={'invoice_id': invoice.id})},
            {'title': 'Xóa mục', 'url': None}
        ]
    }
    return render(request, 'payment/invoice_item_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def record_payment_view(request, invoice_id):
    """Ghi nhận thanh toán thủ công"""
    invoice = get_object_or_404(Invoice, pk=invoice_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.user = invoice.user
            payment.payment_date = timezone.now()
            payment.status = 'completed'
            payment.save()

            invoice.paid_amount += payment.amount
            invoice.save()

            messages.success(request,
                             f'Đã ghi nhận thanh toán {payment.amount} VNĐ cho hóa đơn #{invoice.invoice_number}')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
    else:
        initial_amount = invoice.get_remaining_amount()
        form = PaymentForm(initial={'amount': initial_amount})

    context = {
        'form': form,
        'invoice': invoice,
        'page_title': f'Ghi nhận thanh toán cho hóa đơn #{invoice.invoice_number}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Hóa đơn', 'url': reverse('payment:invoice_list')},
            {'title': f'Hóa đơn #{invoice.invoice_number}',
             'url': reverse('payment:invoice_detail', kwargs={'invoice_id': invoice.id})},
            {'title': 'Ghi nhận thanh toán', 'url': None}
        ]
    }
    return render(request, 'payment/record_payment.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_list_view(request):
    """Danh sách chỉ số điện"""
    readings = ElectricityReading.objects.all().order_by('-year', '-month', 'room__building__name', 'room__room_number')

    room_id = request.GET.get('room')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if room_id:
        readings = readings.filter(room_id=room_id)
    if month:
        readings = readings.filter(month=month)
    if year:
        readings = readings.filter(year=year)

    context = {
        'readings': readings,
        'page_title': 'Danh sách chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': None}
        ]
    }
    return render(request, 'payment/electricity_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_create_view(request):
    """Tạo chỉ số điện mới"""
    if request.method == 'POST':
        form = ElectricityReadingForm(request.POST)
        if form.is_valid():
            reading = form.save()

            messages.success(request, 'Tạo chỉ số điện mới thành công.')
            return redirect('payment:electricity_list')
    else:
        form = ElectricityReadingForm()
        form.initial['reading_date'] = timezone.now().date()
        today = timezone.now().date()
        form.initial['month'] = today.month
        form.initial['year'] = today.year
        form.initial['unit_price'] = 3500

    context = {
        'form': form,
        'page_title': 'Tạo chỉ số điện mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'payment/electricity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_edit_view(request, reading_id):
    """Chỉnh sửa chỉ số điện"""
    reading = get_object_or_404(ElectricityReading, pk=reading_id)

    if request.method == 'POST':
        form = ElectricityReadingForm(request.POST, instance=reading)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật chỉ số điện thành công.')
            return redirect('payment:electricity_list')
    else:
        form = ElectricityReadingForm(instance=reading)

    context = {
        'form': form,
        'reading': reading,
        'page_title': 'Chỉnh sửa chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_list')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'payment/electricity_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def electricity_delete_view(request, reading_id):
    """Xóa chỉ số điện"""
    reading = get_object_or_404(ElectricityReading, pk=reading_id)

    if request.method == 'POST':
        reading.delete()
        messages.success(request, 'Đã xóa chỉ số điện.')
        return redirect('payment:electricity_list')

    context = {
        'reading': reading,
        'page_title': 'Xóa chỉ số điện',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số điện', 'url': reverse('payment:electricity_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'payment/electricity_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_list_view(request):
    readings = (WaterReading.objects.all()
        .order_by('-year', '-month', 'room__building__name', 'room__room_number')
    )

    room_id = request.GET.get('room')
    month = request.GET.get('month')
    year = request.GET.get('year')

    if room_id:
        readings = readings.filter(room_id=room_id)
    if month:
        readings = readings.filter(month=month)
    if year:
        readings = readings.filter(year=year)

    context = {
        'readings': readings,
        'page_title': 'Danh sách chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': None}
        ]
    }
    return render(request, 'payment/water_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_create_view(request):
    if request.method == 'POST':
        form = WaterReadingForm(request.POST)
        if form.is_valid():
            reading = form.save()

            messages.success(request, 'Tạo chỉ số nước mới thành công.')
            return redirect('payment:water_list')
    else:
        form = WaterReadingForm()
        form.initial['reading_date'] = timezone.now().date()
        today = timezone.now().date()
        form.initial['month'] = today.month
        form.initial['year'] = today.year
        form.initial['unit_price'] = 15000

    context = {
        'form': form,
        'page_title': 'Tạo chỉ số nước mới',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_list')},
            {'title': 'Tạo mới', 'url': None}
        ]
    }
    return render(request, 'payment/water_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_edit_view(request, reading_id):
    """Chỉnh sửa chỉ số nước"""
    reading = get_object_or_404(WaterReading, pk=reading_id)

    if request.method == 'POST':
        form = WaterReadingForm(request.POST, instance=reading)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cập nhật chỉ số nước thành công.')
            return redirect('payment:water_list')
    else:
        form = WaterReadingForm(instance=reading)

    context = {
        'form': form,
        'reading': reading,
        'page_title': 'Chỉnh sửa chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_list')},
            {'title': 'Chỉnh sửa', 'url': None}
        ]
    }
    return render(request, 'payment/water_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def water_delete_view(request, reading_id):
    """Xóa chỉ số nước"""
    reading = get_object_or_404(WaterReading, pk=reading_id)

    if request.method == 'POST':
        reading.delete()
        messages.success(request, 'Đã xóa chỉ số nước.')
        return redirect('payment:water_list')

    context = {
        'reading': reading,
        'page_title': 'Xóa chỉ số nước',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Chỉ số nước', 'url': reverse('payment:water_list')},
            {'title': 'Xóa', 'url': None}
        ]
    }
    return render(request, 'payment/water_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def transaction_list_view(request):
    """Danh sách giao dịch"""
    transactions = VNPayTransaction.objects.all().order_by('-created_at')

    user_id = request.GET.get('user')
    status = request.GET.get('status')

    if user_id:
        transactions = transactions.filter(user_id=user_id)
    if status:
        transactions = transactions.filter(transaction_status=status)

    context = {
        'transactions': transactions,
        'page_title': 'Danh sách giao dịch',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Giao dịch', 'url': None}
        ]
    }
    return render(request, 'payment/transaction_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def transaction_detail_view(request, transaction_id):
    """Chi tiết giao dịch"""
    transaction = get_object_or_404(VNPayTransaction, pk=transaction_id)

    context = {
        'transaction': transaction,
        'page_title': f'Chi tiết giao dịch #{transaction.txn_ref}',
        'breadcrumbs': [
            {'title': 'Thanh toán', 'url': '#'},
            {'title': 'Giao dịch', 'url': reverse('payment:transaction_list')},
            {'title': f'Giao dịch #{transaction.txn_ref}', 'url': None}
        ]
    }
    return render(request, 'payment/transaction_detail.html', context)


# ====== API Views ======

@login_required
@user_passes_test(is_admin_or_staff)
def create_invoice_api(request):
    """API tạo hóa đơn"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Chỉ chấp nhận phương thức POST'}, status=405)

    try:
        data = json.loads(request.body) if request.body else request.POST

        user_id = data.get('user_id')
        room_id = data.get('room_id')
        month = int(data.get('month', timezone.now().month))
        year = int(data.get('year', timezone.now().year))

        if not user_id or not room_id:
            return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin người dùng hoặc phòng'}, status=400)

        user = get_object_or_404(User, pk=user_id)
        room = get_object_or_404(Room, pk=room_id)

        contract = Contract.objects.filter(
            user=user,
            room=room,
            status='active',
            start_date__lte=timezone.now().date(),
            end_date__gte=timezone.now().date()
        ).first()

        with transaction.atomic():
            invoice = Invoice.objects.create(
                user=user,
                contract=contract,
                room=room,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=15),
                month=month,
                year=year
            )

            if contract:
                fee_type = FeeType.objects.get_or_create(
                    name='Tiền phòng',
                    code='ROOM_FEE',
                    defaults={'description': 'Phí thuê phòng hàng tháng'}
                )[0]

                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=fee_type,
                    description=f'Tiền phòng tháng {month}/{year}',
                    quantity=1,
                    unit_price=contract.monthly_fee
                )

            electricity_reading = ElectricityReading.objects.filter(
                room=room,
                month=month,
                year=year,
                is_billed=False
            ).first()

            if electricity_reading:
                fee_type = FeeType.objects.get_or_create(
                    name='Tiền điện',
                    code='ELECTRICITY_FEE',
                    defaults={'description': 'Phí sử dụng điện hàng tháng'}
                )[0]

                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=fee_type,
                    description=f'Tiền điện tháng {month}/{year}: {electricity_reading.get_usage()} kWh',
                    quantity=electricity_reading.get_usage(),
                    unit_price=electricity_reading.unit_price
                )

                electricity_reading.is_billed = True
                electricity_reading.invoice = invoice
                electricity_reading.save()

            water_reading = WaterReading.objects.filter(
                room=room,
                month=month,
                year=year,
                is_billed=False
            ).first()

            if water_reading:
                fee_type = FeeType.objects.get_or_create(
                    name='Tiền nước',
                    code='WATER_FEE',
                    defaults={'description': 'Phí sử dụng nước hàng tháng'}
                )[0]

                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_type=fee_type,
                    description=f'Tiền nước tháng {month}/{year}: {water_reading.get_usage()} m³',
                    quantity=water_reading.get_usage(),
                    unit_price=water_reading.unit_price
                )

                water_reading.is_billed = True
                water_reading.invoice = invoice
                water_reading.save()

        return JsonResponse({
            'status': 'success',
            'message': f'Tạo hóa đơn thành công. Số hóa đơn: {invoice.invoice_number}',
            'invoice_id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'redirect': reverse('payment:invoice_detail', kwargs={'invoice_id': invoice.id})
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def check_payment_status_api(request):
    """API kiểm tra trạng thái thanh toán"""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Chỉ chấp nhận phương thức GET'}, status=405)

    try:
        transaction_id = request.GET.get('transaction_id')

        if not transaction_id:
            return JsonResponse({'status': 'error', 'message': 'Thiếu thông tin giao dịch'}, status=400)

        try:
            transaction = VNPayTransaction.objects.get(txn_ref=transaction_id)
        except VNPayTransaction.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Không tìm thấy giao dịch'}, status=404)

        if not is_admin_or_staff(request.user) and transaction.user != request.user:
            return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xem giao dịch này'}, status=403)

        return JsonResponse({
            'status': 'success',
            'transaction_status': transaction.transaction_status,
            'amount': float(transaction.amount),
            'created_at': transaction.created_at.strftime('%d/%m/%Y %H:%M:%S'),
            'transaction_date': transaction.transaction_date.strftime(
                '%d/%m/%Y %H:%M:%S') if transaction.transaction_date else None,
            'response_code': transaction.response_code,
            'message': transaction.response_message
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)