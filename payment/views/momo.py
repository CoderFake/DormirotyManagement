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
import urllib.parse
import datetime
import uuid
import requests

from registration.models import Contract
from payment.models import Payment, Invoice, InvoiceItem, FeeType
from payment.models.momo import MomoTransaction


@login_required
def momo_payment_view(request, invoice_id):
    """Thanh toán hóa đơn qua Momo"""
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
    order_id = f"KTX{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    request_id = f"REQ{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"

    payment = Payment.objects.create(
        invoice=invoice,
        user=request.user,
        amount=amount_to_pay,
        payment_method='momo',
        status='pending'
    )

    momo_transaction = MomoTransaction.objects.create(
        user=request.user,
        payment=payment,
        amount=amount_to_pay,
        order_info=f'Thanh toán hóa đơn {invoice.invoice_number}',
        order_id=order_id,
        request_id=request_id
    )

    partner_code = settings.MOMO_PARTNER_CODE
    access_key = settings.MOMO_ACCESS_KEY
    secret_key = settings.MOMO_SECRET_KEY
    
    # Tạo URL callback và return
    ipn_url = request.build_absolute_uri(reverse('payment:momo_callback'))
    redirect_url = request.build_absolute_uri(reverse('payment:momo_return'))
    
    # Tạo dữ liệu gửi đến Momo
    order_data = {
        "partnerCode": partner_code,
        "accessKey": access_key,
        "requestId": request_id,
        "amount": int(amount_to_pay),
        "orderId": order_id,
        "orderInfo": f"Thanh toán hóa đơn {invoice.invoice_number}",
        "returnUrl": redirect_url,
        "notifyUrl": ipn_url,
        "extraData": "",
        "requestType": "captureMoMoWallet"
    }
    
    # Tạo chữ ký
    raw_signature = f"partnerCode={partner_code}&accessKey={access_key}&requestId={request_id}&amount={int(amount_to_pay)}&orderId={order_id}&orderInfo=Thanh toán hóa đơn {invoice.invoice_number}&returnUrl={redirect_url}&notifyUrl={ipn_url}&extraData="
    signature = hmac.new(secret_key.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()
    order_data["signature"] = signature
    
    # Gửi yêu cầu tạo đơn hàng đến Momo
    try:
        response = requests.post(
            settings.MOMO_PAYMENT_URL,
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        response_data = response.json()
        
        if response_data.get('errorCode') == 0:
            # Lưu thông tin phản hồi
            momo_transaction.response_code = str(response_data.get('errorCode'))
            momo_transaction.save()
            
            # Chuyển hướng đến trang thanh toán Momo
            return redirect(response_data.get('payUrl'))
        else:
            # Xử lý lỗi
            momo_transaction.transaction_status = 'failed'
            momo_transaction.response_code = str(response_data.get('errorCode'))
            momo_transaction.response_message = response_data.get('message')
            momo_transaction.save()
            
            payment.status = 'failed'
            payment.save()
            
            messages.error(request, f'Lỗi tạo giao dịch Momo: {response_data.get("message")}')
            return redirect('payment:invoice_detail', invoice_id=invoice.id)
            
    except Exception as e:
        # Xử lý lỗi kết nối
        momo_transaction.transaction_status = 'failed'
        momo_transaction.response_message = str(e)
        momo_transaction.save()
        
        payment.status = 'failed'
        payment.save()
        
        messages.error(request, f'Lỗi kết nối đến Momo: {str(e)}')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)


@login_required
def momo_deposit_view(request, contract_id):
    """Thanh toán tiền đặt cọc qua Momo"""
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

    # Chuyển hướng đến trang thanh toán Momo
    return momo_payment_view(request, invoice.id)


@csrf_exempt
def momo_callback_view(request):
    """Xử lý callback từ Momo"""
    if request.method == 'POST':
        try:
            # Lấy dữ liệu từ Momo
            data = json.loads(request.body)
            
            # Kiểm tra chữ ký
            partner_code = data.get('partnerCode')
            access_key = data.get('accessKey')
            request_id = data.get('requestId')
            amount = data.get('amount')
            order_id = data.get('orderId')
            order_info = data.get('orderInfo')
            order_type = data.get('orderType')
            transaction_id = data.get('transId')
            error_code = data.get('errorCode')
            message = data.get('message')
            extra_data = data.get('extraData')
            signature = data.get('signature')
            
            # Tạo chuỗi dữ liệu để kiểm tra chữ ký
            raw_signature = f"partnerCode={partner_code}&accessKey={access_key}&requestId={request_id}&amount={amount}&orderId={order_id}&orderInfo={order_info}&orderType={order_type}&transId={transaction_id}&errorCode={error_code}&message={message}&extraData={extra_data}"
            
            # Tạo chữ ký
            secret_key = settings.MOMO_SECRET_KEY
            expected_signature = hmac.new(secret_key.encode(), raw_signature.encode(), hashlib.sha256).hexdigest()
            
            if signature != expected_signature:
                return JsonResponse({
                    "status": 0,
                    "message": "Invalid signature"
                })
            
            # Xử lý giao dịch
            with transaction.atomic():
                momo_transaction = MomoTransaction.objects.get(order_id=order_id)
                
                if error_code == 0:  # Giao dịch thành công
                    momo_transaction.transaction_status = 'success'
                    momo_transaction.transaction_id = transaction_id
                    momo_transaction.transaction_date = timezone.now()
                    momo_transaction.response_code = str(error_code)
                    momo_transaction.response_message = message
                    momo_transaction.save()
                    
                    # Cập nhật payment
                    if momo_transaction.payment:
                        payment = momo_transaction.payment
                        payment.status = 'completed'
                        payment.transaction_id = transaction_id
                        payment.save()
                        
                        # Cập nhật hóa đơn
                        if payment.invoice:
                            invoice = payment.invoice
                            invoice.record_payment(payment.amount, 'momo', transaction_id)
                            
                            # Cập nhật trạng thái hợp đồng nếu là tiền đặt cọc
                            if invoice.contract and invoice.contract.status == 'draft':
                                contract = invoice.contract
                                contract.status = 'pending'
                                contract.save()
                else:
                    momo_transaction.transaction_status = 'failed'
                    momo_transaction.transaction_id = transaction_id
                    momo_transaction.response_code = str(error_code)
                    momo_transaction.response_message = message
                    momo_transaction.save()
                    
                    if momo_transaction.payment:
                        momo_transaction.payment.status = 'failed'
                        momo_transaction.payment.save()
            
            return JsonResponse({
                "status": 1,
                "message": "success",
                "signature": expected_signature
            })
            
        except MomoTransaction.DoesNotExist:
            return JsonResponse({
                "status": 0,
                "message": "Transaction not found"
            })
        except Exception as e:
            return JsonResponse({
                "status": 0,
                "message": f"Error: {str(e)}"
            })
    
    return JsonResponse({
        "status": 0,
        "message": "Invalid request method"
    })


@login_required
def momo_return_view(request):
    """Xử lý kết quả thanh toán từ Momo"""
    # Momo sẽ chuyển hướng người dùng về URL này sau khi thanh toán
    # Lấy thông tin từ URL
    order_id = request.GET.get('orderId')
    error_code = request.GET.get('errorCode')
    
    if not order_id:
        messages.error(request, 'Không tìm thấy thông tin giao dịch.')
        return redirect('dashboard:index')
    
    try:
        momo_transaction = MomoTransaction.objects.get(order_id=order_id)
        
        if error_code == '0':  # Giao dịch thành công
            messages.success(request, 'Thanh toán thành công.')
            
            # Chuyển hướng đến trang chi tiết hợp đồng hoặc hóa đơn
            if momo_transaction.payment and momo_transaction.payment.invoice:
                invoice = momo_transaction.payment.invoice
                if invoice.contract:
                    return redirect('registration:contract_detail', contract_id=invoice.contract.id)
                else:
                    return redirect('payment:invoice_detail', invoice_id=invoice.id)
        else:
            messages.error(request, 'Thanh toán thất bại.')
            return redirect('dashboard:index')
            
    except MomoTransaction.DoesNotExist:
        messages.error(request, 'Không tìm thấy giao dịch.')
        return redirect('dashboard:index')
    except Exception as e:
        messages.error(request, f'Lỗi xử lý giao dịch: {str(e)}')
        return redirect('dashboard:index')
