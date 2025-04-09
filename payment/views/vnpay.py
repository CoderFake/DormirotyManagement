from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import datetime
import uuid
from registration.models import Contract
from payment.models import Payment, Invoice, InvoiceItem, FeeType
from payment.models.vnpay import VNPayTransaction
from ..vnpay_utils import vnpay as VNPayUtil


@login_required
def vnpay_payment_view(request, invoice_id):
    """Thanh toán hóa đơn qua VNPay"""
    invoice = get_object_or_404(Invoice, pk=invoice_id, user=request.user)
    
    if invoice.status not in ['pending', 'partially_paid', 'overdue']:
        messages.error(request, 'Hóa đơn này không trong trạng thái có thể thanh toán.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    amount_to_pay = invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.error(request, 'Hóa đơn này đã được thanh toán đầy đủ.')
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    txn_ref = f"INV{timezone.now().strftime('%y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    order_info = f'Thanh toan hoa don {invoice.invoice_number}' 
    payment = None 
    try:
        with transaction.atomic():
            vnpay_transaction = VNPayTransaction.objects.create(
                user=request.user,
                amount=amount_to_pay,
                order_info=order_info,
                txn_ref=txn_ref
            )
            
            payment = Payment.objects.create(
                invoice=invoice,
                user=request.user,
                amount=amount_to_pay,
                payment_method='vnpay',
                status='pending',
                transaction_id=txn_ref
            )
            
            vnpay_transaction.payment = payment
            vnpay_transaction.save()

    except Exception as e:
        messages.error(request, f"Lỗi khi tạo giao dịch thanh toán: {str(e)}")
        return redirect('payment:invoice_detail', invoice_id=invoice.id)

    vn_pay = VNPayUtil()
    vn_pay.requestData = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(amount_to_pay * 100)),
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': txn_ref,
        'vnp_OrderInfo': order_info,
        'vnp_OrderType': 'billpayment',
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': request.build_absolute_uri(reverse('payment:vnpay_return')),
        'vnp_IpAddr': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S'),
    }

    payment_url = vn_pay.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
    
    return redirect(payment_url)


@login_required
def deposit_payment_view(request, contract_id):
    """Thanh toán tiền đặt cọc qua VNPay sử dụng vnpay_utils."""
    contract = get_object_or_404(Contract, pk=contract_id, user=request.user)

    deposit_invoice = contract.get_deposit_invoice()
    if not deposit_invoice or deposit_invoice.status != 'pending':
        messages.error(request, 'Không tìm thấy hóa đơn đặt cọc hoặc hóa đơn không ở trạng thái chờ thanh toán.')
        return redirect('registration:contract_detail', contract_id=contract.id)

    if contract.status != 'pending_payment':
         messages.warning(request, f'Hợp đồng đang ở trạng thái "{contract.get_status_display()}", không thể thanh toán cọc.')
         return redirect('registration:contract_detail', contract_id=contract.id)

    amount_to_pay = deposit_invoice.get_remaining_amount()
    if amount_to_pay <= 0:
        messages.info(request, 'Hóa đơn đặt cọc này đã được thanh toán.')
        return redirect('registration:contract_detail', contract_id=contract.id)

    txn_ref = f"DEP{timezone.now().strftime('%y%m%d')}{uuid.uuid4().hex[:6].upper()}"
    order_info = f'Thanh toan coc hop dong {contract.contract_number}' # Bỏ dấu tiếng Việt
    payment = None
    try:
        with transaction.atomic():
            vnpay_transaction = VNPayTransaction.objects.create(
                user=request.user,
                amount=amount_to_pay,
                order_info=order_info,
                txn_ref=txn_ref
            )
            
            payment = Payment.objects.create(
                invoice=deposit_invoice,
                user=request.user,
                amount=amount_to_pay,
                payment_method='vnpay',
                status='pending',
                transaction_id=txn_ref
            )
            
            vnpay_transaction.payment = payment
            vnpay_transaction.save()

    except Exception as e:
        messages.error(request, f"Lỗi khi tạo giao dịch thanh toán cọc: {str(e)}")
        return redirect('registration:contract_detail', contract_id=contract.id)

    vn_pay = VNPayUtil()
    vn_pay.requestData = {
        'vnp_Version': '2.1.0',
        'vnp_Command': 'pay',
        'vnp_TmnCode': settings.VNPAY_TMN_CODE,
        'vnp_Amount': str(int(amount_to_pay * 100)),
        'vnp_CurrCode': 'VND',
        'vnp_TxnRef': txn_ref,
        'vnp_OrderInfo': order_info,
        'vnp_OrderType': 'deposit', 
        'vnp_Locale': 'vn',
        'vnp_ReturnUrl': request.build_absolute_uri(reverse('payment:vnpay_return')),
        'vnp_IpAddr': request.META.get('REMOTE_ADDR', '127.0.0.1'),
        'vnp_CreateDate': timezone.now().strftime('%Y%m%d%H%M%S'),
    }

    payment_url = vn_pay.get_payment_url(settings.VNPAY_PAYMENT_URL, settings.VNPAY_HASH_SECRET_KEY)
    
    return redirect(payment_url)


@csrf_exempt
def vnpay_return_view(request):
    """Xử lý kết quả thanh toán từ VNPay (Return URL)"""
    if request.method == 'GET':
        input_data = request.GET.copy()
        if not input_data:
             messages.warning(request, "Không nhận được dữ liệu trả về từ VNPay.")
             return redirect('dashboard:index')

        vn_pay = VNPayUtil()
        vn_pay.responseData = dict(input_data.items())

        if not vn_pay.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            messages.error(request, 'Chữ ký không hợp lệ từ VNPay.')
            return redirect('dashboard:index') 

        txn_ref = vn_pay.responseData.get('vnp_TxnRef')
        response_code = vn_pay.responseData.get('vnp_ResponseCode')
        transaction_no = vn_pay.responseData.get('vnp_TransactionNo')
        bank_code = vn_pay.responseData.get('vnp_BankCode')
        amount = int(vn_pay.responseData.get('vnp_Amount', '0')) / 100
        order_info = vn_pay.responseData.get('vnp_OrderInfo')
        pay_date_str = vn_pay.responseData.get('vnp_PayDate') 

        try:
            vnpay_transaction = VNPayTransaction.objects.select_related('payment', 'payment__invoice', 'payment__invoice__contract').get(txn_ref=txn_ref)
        except VNPayTransaction.DoesNotExist:
            messages.error(request, f"Không tìm thấy giao dịch với mã {txn_ref}.")
            return redirect('dashboard:index')
        
        if vnpay_transaction.payment and vnpay_transaction.payment.status != 'pending':
             messages.info(request, f"Giao dịch {txn_ref} đã được xử lý trước đó.")
             if vnpay_transaction.payment.invoice:
                 if vnpay_transaction.payment.invoice.contract:
                     return redirect('registration:contract_detail', contract_id=vnpay_transaction.payment.invoice.contract.id)
                 else:
                     return redirect('payment:invoice_detail', invoice_id=vnpay_transaction.payment.invoice.id)
             else:
                return redirect('dashboard:index')

        try:
            with transaction.atomic():
                vnpay_transaction.response_code = response_code
                vnpay_transaction.transaction_no = transaction_no
                vnpay_transaction.bank_code = bank_code
                if pay_date_str:
                    try:
                         vnpay_transaction.transaction_date = timezone.make_aware(
                             datetime.datetime.strptime(pay_date_str, '%Y%m%d%H%M%S'), 
                             timezone.get_default_timezone()
                         )
                    except ValueError:
                         vnpay_transaction.transaction_date = timezone.now()
                else:
                     vnpay_transaction.transaction_date = timezone.now()

                if response_code == '00':
                    vnpay_transaction.transaction_status = 'success'
                    vnpay_transaction.save()
                    
                    if vnpay_transaction.payment:
                        payment = vnpay_transaction.payment
                        payment.status = 'completed'
                        payment.transaction_id = transaction_no 
                        payment.payment_date = vnpay_transaction.transaction_date
                        payment.save()

                        if payment.invoice:
                            invoice = payment.invoice
                            invoice.record_payment(payment.amount, 'vnpay', transaction_no)
                            
                            messages.success(request, f'Thanh toán hóa đơn #{invoice.invoice_number} thành công.')
                            
                            if invoice.contract:
                                return redirect('registration:contract_detail', contract_id=invoice.contract.id)
                            else:
                                return redirect('payment:invoice_detail', invoice_id=invoice.id)
                        else:
                             messages.success(request, f'Ghi nhận thanh toán thành công cho giao dịch {txn_ref}.')
                             return redirect('dashboard:index') 
                    else:
                        messages.success(request, f'Giao dịch VNPay {txn_ref} thành công nhưng không liên kết với bản ghi thanh toán nào.')
                        return redirect('dashboard:index')

                else: 
                    vnpay_transaction.transaction_status = 'failed' if response_code else 'cancelled'
                    vnpay_transaction.save()
                    
                    if vnpay_transaction.payment:
                        vnpay_transaction.payment.status = 'failed' if response_code else 'cancelled'
                        vnpay_transaction.payment.save()
                    
                    error_message = settings.VNPAY_RESPONSE_CODES.get(response_code, 'Giao dịch không thành công.')
                    messages.error(request, f'Thanh toán không thành công: {error_message} (Mã lỗi: {response_code})')
                    if vnpay_transaction.payment and vnpay_transaction.payment.invoice:
                         if vnpay_transaction.payment.invoice.contract:
                            return redirect('registration:contract_detail', contract_id=vnpay_transaction.payment.invoice.contract.id)
                         else:
                            return redirect('payment:invoice_detail', invoice_id=vnpay_transaction.payment.invoice.id)
                    else:
                        return redirect('dashboard:index')

        except Exception as e:
            messages.error(request, f"Lỗi khi xử lý kết quả thanh toán: {str(e)}")
            return redirect('dashboard:index')
    else:
        return Http404("Method không hợp lệ")


@csrf_exempt
def vnpay_ipn_view(request):
    """Xử lý Instant Payment Notification (IPN)."""
    if request.method == 'POST':
        input_data = request.POST.copy()
        if not input_data:
            return HttpResponse(VNPayIPNResponse.INVALID_REQUEST, content_type='application/json')

        vn_pay = VNPayUtil()
        vn_pay.responseData = dict(input_data.items())

        if not vn_pay.validate_response(settings.VNPAY_HASH_SECRET_KEY):
            return HttpResponse(VNPayIPNResponse.INVALID_SIGNATURE, content_type='application/json')

        txn_ref = vn_pay.responseData.get('vnp_TxnRef')
        response_code = vn_pay.responseData.get('vnp_ResponseCode')
        transaction_no = vn_pay.responseData.get('vnp_TransactionNo')
        amount = int(vn_pay.responseData.get('vnp_Amount', '0')) / 100
        pay_date_str = vn_pay.responseData.get('vnp_PayDate')

        try:
            vnpay_transaction = VNPayTransaction.objects.select_related('payment', 'payment__invoice').get(txn_ref=txn_ref)
        except VNPayTransaction.DoesNotExist:
            return HttpResponse(VNPayIPNResponse.ORDER_NOT_FOUND, content_type='application/json')

        if vnpay_transaction.amount != amount:
            return HttpResponse(VNPayIPNResponse.INVALID_AMOUNT, content_type='application/json')

        if vnpay_transaction.payment and vnpay_transaction.payment.status == 'completed':
            return HttpResponse(VNPayIPNResponse.ORDER_ALREADY_CONFIRMED, content_type='application/json')

        try:
            with transaction.atomic():
                vnpay_transaction.response_code = response_code
                vnpay_transaction.transaction_no = transaction_no
            
                
                if response_code == '00':
                    vnpay_transaction.transaction_status = 'success'
                    vnpay_transaction.save()

                    if vnpay_transaction.payment:
                        payment = vnpay_transaction.payment
                        payment.status = 'completed'
                        payment.save()
                        
                        if payment.invoice:
                            invoice = payment.invoice
                            invoice.record_payment(payment.amount, 'vnpay_ipn', transaction_no) 

                        return HttpResponse(VNPayIPNResponse.CONFIRM_SUCCESS, content_type='application/json')
                    else:
                         return HttpResponse(VNPayIPNResponse.UNKNOWN_ERROR, content_type='application/json') 
                else:
                    vnpay_transaction.transaction_status = 'failed'
                    vnpay_transaction.save()
                    if vnpay_transaction.payment:
                         vnpay_transaction.payment.status = 'failed'
                         vnpay_transaction.payment.save()
                    
                    return HttpResponse(VNPayIPNResponse.CONFIRM_SUCCESS, content_type='application/json') 
        
        except Exception as e:
            return HttpResponse(VNPayIPNResponse.UNKNOWN_ERROR, content_type='application/json')
    else:
        return Http404("Method không hợp lệ")

class VNPayIPNResponse:
    CONFIRM_SUCCESS = '{"RspCode":"00","Message":"Confirm Success"}'
    ORDER_NOT_FOUND = '{"RspCode":"01","Message":"Order not found"}'
    ORDER_ALREADY_CONFIRMED = '{"RspCode":"02","Message":"Order already confirmed"}'
    INVALID_SIGNATURE = '{"RspCode":"97","Message":"Invalid Signature"}'
    INVALID_AMOUNT = '{"RspCode":"04","Message":"Invalid Amount"}'
    INVALID_REQUEST = '{"RspCode":"99","Message":"Invalid Request"}'
    UNKNOWN_ERROR = '{"RspCode":"99","Message":"Unknown error"}'
