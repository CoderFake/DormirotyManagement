from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Hóa đơn (cho sinh viên)
    path('my-invoices/', views.my_invoices_view, name='my_invoices'),
    path('invoice/<uuid:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),

    # Thanh toán
    path('payment-methods/', views.payment_methods_view, name='payment_methods'),
    path('pay-invoice/<uuid:invoice_id>/', views.pay_invoice_view, name='pay_invoice'),
    path('payment-history/', views.payment_history_view, name='payment_history'),

    # VNPAY
    path('create-payment/', views.create_payment_view, name='create_payment'),
    path('vnpay-return/', views.vnpay_return_view, name='vnpay_return'),
    path('vnpay-ipn/', views.vnpay_ipn_view, name='vnpay_ipn'),

    # Quản lý hóa đơn (cho Admin)
    path('fee-type/list/', views.fee_type_list_view, name='fee_type_list'),
    path('fee-type/create/', views.fee_type_create_view, name='fee_type_create'),
    path('fee-type/<uuid:fee_type_id>/edit/', views.fee_type_edit_view, name='fee_type_edit'),
    path('fee-type/<uuid:fee_type_id>/delete/', views.fee_type_delete_view, name='fee_type_delete'),

    path('invoice/list/', views.invoice_list_view, name='invoice_list'),
    path('invoice/create/', views.invoice_create_view, name='invoice_create'),
    path('invoice/<uuid:invoice_id>/edit/', views.invoice_edit_view, name='invoice_edit'),
    path('invoice/<uuid:invoice_id>/delete/', views.invoice_delete_view, name='invoice_delete'),
    # path('invoice/<uuid:invoice_id>/add-item/', views.invoice_add_item_view, name='invoice_add_item'),
    # path('invoice/item/<uuid:item_id>/edit/', views.invoice_item_edit_view, name='invoice_item_edit'),
    # path('invoice/item/<uuid:item_id>/delete/', views.invoice_item_delete_view, name='invoice_item_delete'),
    # path('invoice/<uuid:invoice_id>/record-payment/', views.record_payment_view, name='record_payment'),
    #
    # # Chỉ số điện nước (cho Admin)
    # path('electricity/list/', views.electricity_list_view, name='electricity_list'),
    # path('electricity/create/', views.electricity_create_view, name='electricity_create'),
    # path('electricity/<uuid:reading_id>/edit/', views.electricity_edit_view, name='electricity_edit'),
    # path('electricity/<uuid:reading_id>/delete/', views.electricity_delete_view, name='electricity_delete'),
    #
    # path('water/list/', views.water_list_view, name='water_list'),
    # path('water/create/', views.water_create_view, name='water_create'),
    # path('water/<uuid:reading_id>/edit/', views.water_edit_view, name='water_edit'),
    # path('water/<uuid:reading_id>/delete/', views.water_delete_view, name='water_delete'),
    #
    # # Giao dịch (cho Admin)
    # path('transaction/list/', views.transaction_list_view, name='transaction_list'),
    # path('transaction/<uuid:transaction_id>/', views.transaction_detail_view, name='transaction_detail'),
    #
    # # API
    # path('api/create-invoice/', views.create_invoice_api, name='create_invoice_api'),
    # path('api/check-payment-status/', views.check_payment_status_api, name='check_payment_status_api'),
]