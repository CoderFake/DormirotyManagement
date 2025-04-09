from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (FeeType, Invoice, InvoiceItem, Payment,
    ElectricityReading, WaterReading
)

from payment.payment_models.vnpay import VNPayTransaction


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ('payment_date', 'transaction_id', 'status')


@admin.register(FeeType)
class FeeTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_recurring', 'is_active')
    list_filter = ('is_recurring', 'is_active')
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'user', 'room', 'issue_date', 'due_date', 'total_amount', 'paid_amount', 'status')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'user__full_name', 'user__email', 'notes')
    date_hierarchy = 'issue_date'
    ordering = ('-issue_date',)
    inlines = [InvoiceItemInline, PaymentInline]
    readonly_fields = ('invoice_number', 'total_amount', 'paid_amount')


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'fee_type', 'description', 'quantity', 'unit_price', 'amount')
    list_filter = ('fee_type',)
    search_fields = ('description', 'invoice__invoice_number')
    readonly_fields = ('amount',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'invoice', 'amount', 'payment_date', 'payment_method', 'status')
    list_filter = ('status', 'payment_method', 'payment_date')
    search_fields = ('user__full_name', 'user__email', 'invoice__invoice_number', 'transaction_id')
    date_hierarchy = 'payment_date'
    readonly_fields = ('payment_date',)


@admin.register(ElectricityReading)
class ElectricityReadingAdmin(admin.ModelAdmin):
    list_display = ('room', 'month', 'year', 'reading_date', 'previous_reading', 'current_reading', 'get_usage', 'unit_price', 'amount', 'is_billed')
    list_filter = ('month', 'year', 'is_billed', 'reading_date')
    search_fields = ('room__room_number', 'room__building__name')
    date_hierarchy = 'reading_date'
    readonly_fields = ('amount',)


@admin.register(WaterReading)
class WaterReadingAdmin(admin.ModelAdmin):
    list_display = ('room', 'month', 'year', 'reading_date', 'previous_reading', 'current_reading', 'get_usage', 'unit_price', 'amount', 'is_billed')
    list_filter = ('month', 'year', 'is_billed', 'reading_date')
    search_fields = ('room__room_number', 'room__building__name')
    date_hierarchy = 'reading_date'
    readonly_fields = ('amount',)


@admin.register(VNPayTransaction)
class VNPayTransactionAdmin(admin.ModelAdmin):
    list_display = ('txn_ref', 'user', 'amount', 'transaction_status', 'created_at', 'transaction_date')
    list_filter = ('transaction_status', 'created_at')
    search_fields = ('txn_ref', 'user__full_name', 'user__email', 'order_info', 'transaction_no')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'user', 'payment', 'txn_ref', 'amount', 'order_info',
        'transaction_no', 'bank_code', 'card_type', 'transaction_date',
        'response_code', 'response_message', 'secure_hash'
    )