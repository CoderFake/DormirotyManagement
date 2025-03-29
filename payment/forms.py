from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from .models import FeeType, Invoice, InvoiceItem, Payment, ElectricityReading, WaterReading


class FeeTypeForm(forms.ModelForm):
    """Form loại phí"""

    class Meta:
        model = FeeType
        fields = ['name', 'code', 'description', 'is_recurring', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class InvoiceForm(forms.ModelForm):
    """Form hóa đơn"""

    class Meta:
        model = Invoice
        fields = ['user', 'contract', 'room', 'due_date', 'notes', 'month', 'year']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'contract': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2050}),
        }

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        contract = cleaned_data.get('contract')
        room = cleaned_data.get('room')

        if contract and contract.user != user:
            raise forms.ValidationError("Hợp đồng không thuộc về người dùng đã chọn")

        if contract and contract.room != room:
            raise forms.ValidationError("Phòng không khớp với thông tin hợp đồng")

        return cleaned_data


class InvoiceItemForm(forms.ModelForm):
    """Form mục hóa đơn"""

    class Meta:
        model = InvoiceItem
        fields = ['fee_type', 'description', 'quantity', 'unit_price']
        widgets = {
            'fee_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
        }


class PaymentForm(forms.ModelForm):
    """Form thanh toán"""

    class Meta:
        model = Payment
        fields = ['amount', 'payment_method', 'transaction_id', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'transaction_id': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ElectricityReadingForm(forms.ModelForm):
    """Form chỉ số điện"""

    class Meta:
        model = ElectricityReading
        fields = ['room', 'month', 'year', 'reading_date', 'previous_reading', 'current_reading', 'unit_price', 'notes']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2050}),
            'reading_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'previous_reading': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'current_reading': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        previous_reading = cleaned_data.get('previous_reading')
        current_reading = cleaned_data.get('current_reading')

        if current_reading < previous_reading:
            raise forms.ValidationError("Chỉ số mới không thể nhỏ hơn chỉ số cũ")

        room = cleaned_data.get('room')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        if room and month and year:
            existing = ElectricityReading.objects.filter(room=room, month=month, year=year)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("Đã tồn tại chỉ số điện cho phòng này trong tháng đã chọn")

        return cleaned_data


class WaterReadingForm(forms.ModelForm):
    """Form chỉ số nước"""

    class Meta:
        model = WaterReading
        fields = ['room', 'month', 'year', 'reading_date', 'previous_reading', 'current_reading', 'unit_price', 'notes']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'month': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2050}),
            'reading_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'previous_reading': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'current_reading': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        previous_reading = cleaned_data.get('previous_reading')
        current_reading = cleaned_data.get('current_reading')

        if current_reading < previous_reading:
            raise forms.ValidationError("Chỉ số mới không thể nhỏ hơn chỉ số cũ")

        room = cleaned_data.get('room')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        if room and month and year:
            existing = WaterReading.objects.filter(room=room, month=month, year=year)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("Đã tồn tại chỉ số nước cho phòng này trong tháng đã chọn")

        return cleaned_data


class VNPayPaymentForm(forms.Form):
    """Form tạo thanh toán VNPAY"""

    amount = forms.DecimalField(
        label=_('Số tiền'),
        min_value=Decimal('10000'),
        max_value=Decimal('100000000'),
        decimal_places=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 10000, 'step': 1000})
    )

    order_info = forms.CharField(
        label=_('Nội dung thanh toán'),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return (amount // 1000) * 1000