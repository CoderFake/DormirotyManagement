from django.urls import path
from .views import vnpay, zalopay, momo, invoice, utility, room_fee, deposit, fee_type

app_name = 'payment'

urlpatterns = [
    # Invoice management
    path('invoices/', invoice.invoice_list_view, name='invoice_list'),
    path('invoices/create/', invoice.invoice_create_view, name='invoice_create'),
    path('invoices/<uuid:invoice_id>/', invoice.invoice_detail_view, name='invoice_detail'),
    path('invoices/<uuid:invoice_id>/edit/', invoice.invoice_edit_view, name='invoice_edit'),
    path('invoices/<uuid:invoice_id>/delete/', invoice.invoice_delete_view, name='invoice_delete'),
    
    # Invoice items
    path('payment-history/', invoice.payment_history_view, name='payment_history'),
    path('invoices/<uuid:invoice_id>/pay/', invoice.pay_invoice_view, name='pay_invoice'),
    path('my-invoices/', invoice.my_invoices_view, name='my_invoices'),
    path('invoices/<uuid:invoice_id>/items/add/', invoice.invoice_item_create_view, name='invoice_item_create'),
    path('invoice-items/<uuid:item_id>/edit/', invoice.invoice_item_edit_view, name='invoice_item_edit'),
    path('invoice-items/<uuid:item_id>/delete/', invoice.invoice_item_delete_view, name='invoice_item_delete'),
    path('invoices/<uuid:invoice_id>/items/add-ajax/', invoice.invoice_item_create_ajax, name='invoice_item_create_ajax'),
    
    # Payment recording
    path('invoices/<uuid:invoice_id>/record-payment/', invoice.record_payment_view, name='record_payment'),
    path('invoices/<uuid:invoice_id>/payment-methods/', deposit.payment_methods_view, name='payment_methods'),
    
    # Deposit payment
    path('deposit/<uuid:contract_id>/', deposit.deposit_payment_view, name='deposit_payment'),

    # Payment methods
    path('payment-methods/', deposit.payment_methods_view, name='payment_methods'),
    path('invoices/<uuid:invoice_id>/payment-methods/', deposit.payment_methods_view, name='payment_methods'),
    
    # VNPAY integration
    path('vnpay/pay/<uuid:invoice_id>/', vnpay.vnpay_payment_view, name='vnpay_payment'),
    path('vnpay/return/', vnpay.vnpay_return_view, name='vnpay_return'),
    path('vnpay/ipn/', vnpay.vnpay_ipn_view, name='vnpay_ipn'),
    
    # ZaloPay integration
    path('zalopay/pay/<uuid:invoice_id>/', zalopay.zalopay_payment_view, name='zalopay_payment'),
    path('zalopay/return/', zalopay.zalopay_return_view, name='zalopay_return'),
    path('zalopay/callback/', zalopay.zalopay_callback_view, name='zalopay_callback'),
    
    # Momo integration
    path('momo/pay/<uuid:invoice_id>/', momo.momo_payment_view, name='momo_payment'),
    path('momo/return/', momo.momo_return_view, name='momo_return'),
    path('momo/callback/', momo.momo_callback_view, name='momo_callback'),
    
    # Utility readings
    path('electricity/', utility.electricity_reading_list_view, name='electricity_reading_list'),
    path('electricity/create/', utility.electricity_reading_create_view, name='electricity_reading_create'),
    path('electricity/<uuid:reading_id>/edit/', utility.electricity_reading_edit_view, name='electricity_reading_edit'),
    path('electricity/<uuid:reading_id>/delete/', utility.electricity_reading_delete_view, name='electricity_reading_delete'),
    
    path('water/', utility.water_reading_list_view, name='water_reading_list'),
    path('water/create/', utility.water_reading_create_view, name='water_reading_create'),
    path('water/<uuid:reading_id>/edit/', utility.water_reading_edit_view, name='water_reading_edit'),
    path('water/<uuid:reading_id>/delete/', utility.water_reading_delete_view, name='water_reading_delete'),
    
    # Invoice generation
    path('generate/room-fee/', room_fee.generate_room_fee_invoices, name='generate_room_fee_invoices'),
    path('generate/utility/', room_fee.generate_utility_invoices, name='generate_utility_invoices'),
    
    # Export
    path('invoices/export/csv/', invoice.export_invoices_csv, name='export_invoices_csv'),

    #fee
    path('fee-types/', fee_type.fee_type_list_view, name='fee_type_list'),
    path('fee-types/create/', fee_type.fee_type_create_view, name='fee_type_create'),
    path('fee-types/<uuid:fee_type_id>/edit/', fee_type.fee_type_edit_view, name='fee_type_edit'),
    path('fee-types/<uuid:fee_type_id>/delete/', fee_type.fee_type_delete_view, name='fee_type_delete'),
]
