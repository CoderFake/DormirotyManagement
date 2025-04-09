from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import hashlib
import hmac
import json
import datetime
import uuid
import requests
import base64

from registration.models import Contract
from payment.models import Payment, Invoice, InvoiceItem, FeeType
from payment.models.zalopay import ZaloPayTransaction


@login_required
def zalopay_payment_view(request, invoice_id):
    """Thanh toán hóa đơn qua ZaloPay"""
    invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    if invoice.status not in ['pending', 'partially_paid', 'overdue']:
        messages.error(request, 'Hóa đơn này không trong trạng thái có thể thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    # Tính số tiền cần thanh toán
    amount_to_pay = invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.error(request, 'Hóa đơn này đã được thanh toán đầy đủ.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    # Tạo mã giao dịch
    app_trans_id = f"KTX{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    
    # Tạo payment record
    payment = Payment.objects.create(
        invoice=invoice,
        user=request.user,
        amount=amount_to_pay,
        payment_method='zalopay',
        status='pending'
    )
    
    # Tạo giao dịch ZaloPay
    zalopay_transaction = ZaloPayTransaction.objects.create(
        user=request.user,
        payment=payment,
        amount=amount_to_pay,
        order_info=f'Thanh toán hóa đơn {invoice.invoice_number}',
        app_trans_id=app_trans_id
    )
    
    # Tạo dữ liệu thanh toán ZaloPay
    app_id = settings.ZALOPAY_APP_ID
    app_user = request.user.username
    embed_data = json.dumps({
        "redirecturl": request.build_absolute_uri(reverse('payment:zalopay_return'))
    })
    item = json.dumps([])
    app_time = int(timezone.now().timestamp() * 1000)  # Thời gian hiện tại (milliseconds)
    
    # Tạo chuỗi dữ liệu để tạo chữ ký
    data = f"{app_id}|{app_trans_id}|{app_user}|{amount_to_pay}|{app_time}|{embed_data}|{item}"
    
    # Tạo chữ ký
    key1 = settings.ZALOPAY_KEY1
    mac = hmac.new(key1.encode(), data.encode(), hashlib.sha256).hexdigest()
    
    # Tạo dữ liệu gửi đến ZaloPay
    order_data = {
        "app_id": app_id,
        "app_trans_id": app_trans_id,
        "app_user": app_user,
        "app_time": app_time,
        "amount": int(amount_to_pay),
        "item": item,
        "embed_data": embed_data,
        "description": f"Thanh toán hóa đơn {invoice.invoice_number}",
        "mac": mac
    }
    
    # Gửi yêu cầu tạo đơn hàng đến ZaloPay
    try:
        response = requests.post(
            settings.ZALOPAY_CREATE_ORDER_URL,
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        response_data = response.json()
        
        if response_data.get('return_code') == 1:
            # Lưu thông tin phản hồi
            zalopay_transaction.response_code = str(response_data.get('return_code'))
            zalopay_transaction.save()
            
            # Chuyển hướng đến trang thanh toán ZaloPay
            return redirect(response_data.get('order_url'))
        else:
            # Xử lý lỗi
            zalopay_transaction.transaction_status = 'failed'
            zalopay_transaction.response_code = str(response_data.get('return_code'))
            zalopay_transaction.response_message = response_data.get('return_message')
            zalopay_transaction.save()
            
            payment.status = 'failed'
            payment.save()
            
            messages.error(request, f'Lỗi tạo giao dịch ZaloPay: {response_data.get("return_message")}')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
            
    except Exception as e:
        # Xử lý lỗi kết nối
        zalopay_transaction.transaction_status = 'failed'
        zalopay_transaction.response_message = str(e)
        zalopay_transaction.save()
        
        payment.status = 'failed'
        payment.save()
        
        messages.error(request, f'Lỗi kết nối đến ZaloPay: {str(e)}')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)


@login_required
def zalopay_deposit_view(request, contract_id):
    """Thanh toán tiền đặt cọc qua ZaloPay"""
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

    # Chuyển hướng đến trang thanh toán ZaloPay
    return zalopay_payment_view(request, invoice.id)


@csrf_exempt
def zalopay_callback_view(request):
    """Xử lý callback từ ZaloPay"""
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ ZaloPay
            data = json.loads(request.body)
            
            # Kiểm tra chữ ký
            app_id = data.get('app_id')
            app_trans_id = data.get('app_trans_id')
            zp_trans_id = data.get('zp_trans_id')
            amount = data.get('amount')
            server_time = data.get('server_time')
            status = data.get('status')
            mac = data.get('mac')
            
            # Tạo chuỗi dữ liệu để kiểm tra chữ ký
            data_str = f"{app_id}|{app_trans_id}|{zp_trans_id}|{amount}|{server_time}|{status}"
            
            # Tạo chữ ký
            key2 = settings.ZALOPAY_KEY2
            expected_mac = hmac.new(key2.encode(), data_str.encode(), hashlib.sha256).hexdigest()
            
            if mac != expected_mac:
                return JsonResponse({
                    "return_code": -1,
                    "return_message": "Invalid signature"
                })
            
            # Xử lý giao dịch
            with transaction.atomic():
                zalopay_transaction = ZaloPayTransaction.objects.get(app_trans_id=app_trans_id)
                
                if status == 1:  # Giao dịch thành công
                    zalopay_transaction.transaction_status = 'success'
                    zalopay_transaction.zp_trans_id = zp_trans_id
                    zalopay_transaction.transaction_date = timezone.now()
                    zalopay_transaction.response_code = str(status)
                    zalopay_transaction.save()
                    
                    # Cập nhật payment
                    if zalopay_transaction.payment:
                        payment = zalopay_transaction.payment
                        payment.status = 'completed'
                        payment.transaction_id = zp_trans_id
                        payment.save()
                        
                        # Cập nhật hóa đơn
                        if payment.invoice:
                            invoice = payment.invoice
                            invoice.record_payment(payment.amount, 'zalopay', zp_trans_id)
                            
                            # Cập nhật trạng thái hợp đồng nếu là tiền đặt cọc
                            if invoice.contract and invoice.contract.status == 'draft':
                                contract = invoice.contract
                                contract.status = 'pending'
                                contract.save()
                else:
                    zalopay_transaction.transaction_status = 'failed'
                    zalopay_transaction.zp_trans_id = zp_trans_id
                    zalopay_transaction.response_code = str(status)
                    zalopay_transaction.save()
                    
                    if zalopay_transaction.payment:
                        zalopay_transaction.payment.status = 'failed'
                        zalopay_transaction.payment.save()
            
            return JsonResponse({
                "return_code": 1,
                "return_message": "success"
            })
            
        except ZaloPayTransaction.DoesNotExist:
            return JsonResponse({
                "return_code": -2,
                "return_message": "Transaction not found"
            })
        except Exception as e:
            return JsonResponse({
                "return_code": -3,
                "return_message": f"Error: {str(e)}"
            })
    
    return JsonResponse({
        "return_code": -4,
        "return_message": "Invalid request method"
    })


@login_required
def zalopay_return_view(request):
    """Xử lý kết quả thanh toán từ ZaloPay"""
    # ZaloPay sẽ chuyển hướng người dùng về URL này sau khi thanh toán
    # Kiểm tra trạng thái giao dịch gần nhất của người dùng
    try:
        zalopay_transaction = ZaloPayTransaction.objects.filter(
            user=request.user
        ).order_by('-created_at').first()
        
        if not zalopay_transaction:
            messages.error(request, 'Không tìm thấy giao dịch.')
            return redirect('dashboard:index')
        
        if zalopay_transaction.transaction_status == 'success':
            messages.success(request, 'Thanh toán thành công.')
            
            # Chuyển hướng đến trang chi tiết hợp đồng hoặc hóa đơn
            if zalopay_transaction.payment and zalopay_transaction.payment.invoice:
                invoice = zalopay_transaction.payment.invoice
                if invoice.contract:
                    return redirect('registration:contract_detail', contract_id=invoice.contract.id)
                else:
                    return redirect('payment:invoice_detail', invoice_id=invoice.id)
        elif zalopay_transaction.transaction_status == 'pending':
            # Kiểm tra trạng thái giao dịch với ZaloPay
            app_id = settings.ZALOPAY_APP_ID
            app_trans_id = zalopay_transaction.app_trans_id
            key1 = settings.ZALOPAY_KEY1
            
            # Tạo chuỗi dữ liệu để tạo chữ ký
            data = f"{app_id}|{app_trans_id}|{key1}"
            mac = hmac.new(key1.encode(), data.encode(), hashlib.sha256).hexdigest()
            
            # Gửi yêu cầu kiểm tra trạng thái đến ZaloPay
            try:
                response = requests.post(
                    settings.ZALOPAY_QUERY_ORDER_URL,
                    json={
                        "app_id": app_id,
                        "app_trans_id": app_trans_id,
                        "mac": mac
                    },
                    headers={"Content-Type": "application/json"}
                )
                
                response_data = response.json()
                
                if response_data.get('return_code') == 1:
                    # Cập nhật trạng thái giao dịch
                    with transaction.atomic():
                        if response_data.get('status') == 1:  # Giao dịch thành công
                            zalopay_transaction.transaction_status = 'success'
                            zalopay_transaction.zp_trans_id = response_data.get('zp_trans_id')
                            zalopay_transaction.transaction_date = timezone.now()
                            zalopay_transaction.response_code = str(response_data.get('status'))
                            zalopay_transaction.save()
                            
                            # Cập nhật payment
                            if zalopay_transaction.payment:
                                payment = zalopay_transaction.payment
                                payment.status = 'completed'
                                payment.transaction_id = response_data.get('zp_trans_id')
                                payment.save()
                                
                                # Cập nhật hóa đơn
                                if payment.invoice:
                                    invoice = payment.invoice
                                    invoice.record_payment(payment.amount, 'zalopay', response_data.get('zp_trans_id'))
                                    
                                    # Cập nhật trạng thái hợp đồng nếu là tiền đặt cọc
                                    if invoice.contract and invoice.contract.status == 'draft':
                                        contract = invoice.contract
                                        contract.status = 'pending'
                                        contract.save()
                            
                            messages.success(request, 'Thanh toán thành công.')
                            
                            # Chuyển hướng đến trang chi tiết hợp đồng hoặc hóa đơn
                            if zalopay_transaction.payment and zalopay_transaction.payment.invoice:
                                invoice = zalopay_transaction.payment.invoice
                                if invoice.contract:
                                    return redirect('registration:contract_detail', contract_id=invoice.contract.id)
                                else:
                                    return redirect('payment:invoice_detail', invoice_id=invoice.id)
                        else:
                            zalopay_transaction.transaction_status = 'failed'
                            zalopay_transaction.response_code = str(response_data.get('status'))
                            zalopay_transaction.save()
                            
                            if zalopay_transaction.payment:
                                zalopay_transaction.payment.status = 'failed'
                                zalopay_transaction.payment.save()
                            
                            messages.error(request, 'Thanh toán thất bại.')
                            return redirect('dashboard:index')
                else:
                    messages.error(request, f'Lỗi kiểm tra trạng thái giao dịch: {response_data.get("return_message")}')
                    return redirect('dashboard:index')
                    
            except Exception as e:
                messages.error(request, f'Lỗi kết nối đến ZaloPay: {str(e)}')
                return redirect('dashboard:index')
        else:
            messages.error(request, 'Thanh toán thất bại.')
            return redirect('dashboard:index')
            
    except Exception as e:
        messages.error(request, f'Lỗi xử lý giao dịch: {str(e)}')
        return redirect('dashboard:index')
