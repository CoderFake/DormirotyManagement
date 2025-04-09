from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import hashlib
import hmac
import urllib.parse
import datetime
import uuid

from registration.models import Contract
from payment.models import Payment, Invoice, InvoiceItem, FeeType
from payment.models.vnpay import VNPayTransaction


@login_required
def vnpay_payment_view(request, invoice_id):
    """Thanh toán hóa đơn qua VNPay"""
    invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    if invoice.status not in ['pending', 'partially_paid', 'overdue']:
        messages.error(request, 'Hóa đơn này không trong trạng thái có thể thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    # Tính số tiền cần thanh toán
    amount_to_pay = invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.error(request, 'Hóa đơn này đã được thanh toán đầy đủ.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    # Tạo giao dịch VNPay
    txn_ref = f"KTX{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    
    vnpay_transaction = VNPayTransaction.objects.create(
        user=request.user,
        amount=amount_to_pay,
        order_info=f'Thanh toán hóa đơn {invoice.invoice_number}',
        txn_ref=txn_ref
    )
    
    # Tạo payment record
    payment = Payment.objects.create(
        invoice=invoice,
        user=request.user,
        amount=amount_to_pay,
        payment_method='vnpay',
        status='pending'
    )
    
    vnpay_transaction.payment = payment
    vnpay_transaction.save()
    
    # Tạo URL thanh toán VNPay
    vnp_params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(amount_to_pay * 100)),  # Số tiền * 100 (VNĐ)
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': txn_ref,
        'vnp_OrderInfo': f'Thanh toan hoa don {invoice.invoice_number}',
        'vnp_OrderType': 'billpayment',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': request.build_absolute_uri(reverse('payment:vnpay_return')),
        'vnp_IpAddr': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S')
    }
    
    # Sắp xếp params theo key
    sorted_params = sorted(vnp_params.items(), key=lambda x: x[0])
    hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])
    
    # Tạo chữ ký
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    secure_hash = hmac.new(
        secret_key.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    vnp_params['vnp_SecureHash'] = secure_hash
    vnpay_url = settings.VNPAY_PAYMENT_URL + '?' + urllib.parse.urlencode(vnp_params)
    
    return redirect(vnpay_url)


@login_required
def deposit_payment_view(request, contract_id):
    """Thanh toán tiền đặt cọc qua VNPay"""
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

    # Tạo giao dịch VNPay
    txn_ref = f"KTX{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
    
    vnpay_transaction = VNPayTransaction.objects.create(
        user=request.user,
        amount=invoice.total_amount,
        order_info=f'Thanh toán tiền đặt cọc hợp đồng {contract.contract_number}',
        txn_ref=txn_ref
    )
    
    # Tạo payment record
    payment = Payment.objects.create(
        invoice=invoice,
        user=request.user,
        amount=invoice.total_amount,
        payment_method='vnpay',
        status='pending'
    )
    
    vnpay_transaction.payment = payment
    vnpay_transaction.save()
    
    # Tạo URL thanh toán VNPay
    vnp_params = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(invoice.total_amount * 100)),  # Số tiền * 100 (VNĐ)
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': txn_ref,
        'vnp_OrderInfo': f'Thanh toan tien dat coc hop dong {contract.contract_number}',
        'vnp_OrderType': 'deposit',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': request.build_absolute_uri(reverse('payment:vnpay_return')),
        'vnp_IpAddr': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S')
    }
    
    # Sắp xếp params theo key
    sorted_params = sorted(vnp_params.items(), key=lambda x: x[0])
    hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])
    
    # Tạo chữ ký
    secret_key = settings.VNPAY_HASH_SECRET_KEY
    secure_hash = hmac.new(
        secret_key.encode('utf-8'),
        hash_data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()
    
    vnp_params['vnp_SecureHash'] = secure_hash
    vnpay_url = settings.VNPAY_PAYMENT_URL + '?' + urllib.parse.urlencode(vnp_params)
    
    return redirect(vnpay_url)


@csrf_exempt
def vnpay_return_view(request):
    """Xử lý kết quả thanh toán từ VNPay"""
    if request.method == 'GET':
        # Lấy thông tin từ VNPay trả về
        vnp_params = request.GET.copy()
        secure_hash = vnp_params.pop('vnp_SecureHash', [''])[0]
        
        # Kiểm tra chữ ký
        sorted_params = sorted(vnp_params.items(), key=lambda x: x[0])
        hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])
        
        calculated_hash = hmac.new(
            settings.VNPAY_HASH_SECRET_KEY.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        if secure_hash != calculated_hash:
            messages.error(request, 'Chữ ký không hợp lệ.')
            return redirect('dashboard:index')
        
        # Lấy thông tin giao dịch
        txn_ref = vnp_params.get('vnp_TxnRef', [''])[0]
        response_code = vnp_params.get('vnp_ResponseCode', [''])[0]
        transaction_no = vnp_params.get('vnp_TransactionNo', [''])[0]
        bank_code = vnp_params.get('vnp_BankCode', [''])[0]
        
        try:
            with transaction.atomic():
                vnpay_transaction = VNPayTransaction.objects.get(txn_ref=txn_ref)
                
                if response_code == '00':  # Giao dịch thành công
                    vnpay_transaction.transaction_status = 'success'
                    vnpay_transaction.transaction_no = transaction_no
                    vnpay_transaction.bank_code = bank_code
                    vnpay_transaction.transaction_date = timezone.now()
                    vnpay_transaction.response_code = response_code
                    vnpay_transaction.save()
                    
                    # Cập nhật payment
                    if vnpay_transaction.payment:
                        payment = vnpay_transaction.payment
                        payment.status = 'completed'
                        payment.transaction_id = transaction_no
                        payment.save()
                        
                        # Cập nhật hóa đơn
                        if payment.invoice:
                            invoice = payment.invoice
                            invoice.record_payment(payment.amount, 'vnpay', transaction_no)
                            
                            # Cập nhật trạng thái hợp đồng nếu là tiền đặt cọc
                            if invoice.contract and invoice.contract.status == 'draft':
                                contract = invoice.contract
                                contract.status = 'pending'
                                contract.save()
                            
                            messages.success(request, 'Thanh toán thành công.')
                            
                            if invoice.contract:
                                return redirect('registration:contract_detail', contract_id=invoice.contract.id)
                            else:
                                return redirect('payment:invoice_detail', invoice_id=invoice.id)
                else:
                    vnpay_transaction.transaction_status = 'failed'
                    vnpay_transaction.response_code = response_code
                    vnpay_transaction.save()
                    
                    if vnpay_transaction.payment:
                        vnpay_transaction.payment.status = 'failed'
                        vnpay_transaction.payment.save()
                    
                    messages.error(request, 'Thanh toán thất bại.')
                    return redirect('dashboard:index')
                    
        except VNPayTransaction.DoesNotExist:
            messages.error(request, 'Không tìm thấy giao dịch.')
            return redirect('dashboard:index')
        except Exception as e:
            messages.error(request, f'Lỗi xử lý giao dịch: {str(e)}')
            return redirect('dashboard:index')
    
    return HttpResponse('Invalid request method')


@csrf_exempt
def vnpay_ipn_view(request):
    """Xử lý IPN (Instant Payment Notification) từ VNPay"""
    if request.method == 'GET':
        vnp_params = request.GET.copy()
        secure_hash = vnp_params.pop('vnp_SecureHash', [''])[0]
        
        # Kiểm tra chữ ký
        sorted_params = sorted(vnp_params.items(), key=lambda x: x[0])
        hash_data = '&'.join([f'{k}={v}' for k, v in sorted_params])
        
        calculated_hash = hmac.new(
            settings.VNPAY_HASH_SECRET_KEY.encode('utf-8'),
            hash_data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        if secure_hash != calculated_hash:
            return HttpResponse('Invalid signature')
        
        # Xử lý thông tin giao dịch
        txn_ref = vnp_params.get('vnp_TxnRef', [''])[0]
        response_code = vnp_params.get('vnp_ResponseCode', [''])[0]
        transaction_no = vnp_params.get('vnp_TransactionNo', [''])[0]
        
        try:
            vnpay_transaction = VNPayTransaction.objects.get(txn_ref=txn_ref)
            
            if response_code == '00':  # Giao dịch thành công
                if vnpay_transaction.transaction_status != 'success':
                    with transaction.atomic():
                        vnpay_transaction.transaction_status = 'success'
                        vnpay_transaction.transaction_no = transaction_no
                        vnpay_transaction.response_code = response_code
                        vnpay_transaction.save()
                        
                        # Cập nhật payment và invoice nếu cần
                        if vnpay_transaction.payment:
                            payment = vnpay_transaction.payment
                            payment.status = 'completed'
                            payment.transaction_id = transaction_no
                            payment.save()
                            
                            if payment.invoice:
                                invoice = payment.invoice
                                invoice.record_payment(payment.amount, 'vnpay', transaction_no)
                                
                                # Cập nhật trạng thái hợp đồng nếu là tiền đặt cọc
                                if invoice.contract and invoice.contract.status == 'draft':
                                    contract = invoice.contract
                                    contract.status = 'pending'
                                    contract.save()
            
            return HttpResponse('OK')
            
        except VNPayTransaction.DoesNotExist:
            return HttpResponse('Transaction not found')
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}')
    
    return HttpResponse('Invalid request method')
