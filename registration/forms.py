from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from dormitory.models import Building, Room, Bed, RoomType
from .models import RegistrationPeriod, RoomRegistration, Contract, CheckIn, CheckOut


class RegistrationPeriodForm(forms.ModelForm):
    """Form kỳ đăng ký"""

    class Meta:
        model = RegistrationPeriod
        fields = [
            'name', 'academic_year', 'semester', 'registration_start', 'registration_end',
            'check_in_start', 'check_in_end', 'contract_start', 'contract_end',
            'description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control'}),
            'semester': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_start': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'registration_end': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'check_in_start': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'check_in_end': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'contract_start': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'contract_end': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoomRegistrationForm(forms.ModelForm):
    """Form đăng ký phòng"""

    preferred_building = forms.ModelChoiceField(
        queryset=Building.objects.filter(is_active=True),
        label=_('Tòa nhà mong muốn'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    preferred_room_type = forms.ModelChoiceField(
        queryset=RoomType.objects.filter(is_active=True),
        label=_('Loại phòng mong muốn'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = RoomRegistration
        fields = ['preferred_building', 'preferred_room_type', 'special_requirements']
        widgets = {
            'special_requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }


class ContractForm(forms.ModelForm):
    """Form hợp đồng"""

    class Meta:
        model = Contract
        fields = [
            'room', 'bed', 'start_date', 'end_date', 'monthly_fee',
            'deposit_amount', 'terms_and_conditions', 'notes'
        ]
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'bed': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ContractApprovalForm(forms.Form):
    """Form phê duyệt hợp đồng"""

    notes = forms.CharField(
        label=_('Ghi chú'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class CheckInForm(forms.ModelForm):
    """Form nhận phòng"""

    class Meta:
        model = CheckIn
        fields = ['room_condition', 'items_received', 'notes', 'is_completed']
        widgets = {
            'room_condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'items_received': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CheckOutForm(forms.ModelForm):
    """Form trả phòng"""

    class Meta:
        model = CheckOut
        fields = ['room_condition', 'damage_description', 'damage_charges', 'notes', 'is_completed']
        widgets = {
            'room_condition': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'damage_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'damage_charges': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoomSelectionForm(forms.Form):
    """Form chọn phòng"""

    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_active=True, status__in=['available', 'partially_occupied']),
        label=_('Phòng'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        building_id = kwargs.pop('building_id', None)
        room_type_id = kwargs.pop('room_type_id', None)
        super().__init__(*args, **kwargs)

        rooms = Room.objects.filter(is_active=True, status__in=['available', 'partially_occupied'])
        if building_id:
            rooms = rooms.filter(building_id=building_id)
        if room_type_id:
            rooms = rooms.filter(room_type_id=room_type_id)

        self.fields['room'].queryset = rooms


class BedSelectionForm(forms.Form):
    """Form chọn giường"""

    bed = forms.ModelChoiceField(
        queryset=Bed.objects.filter(status='available'),
        label=_('Giường'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        room_id = kwargs.pop('room_id', None)
        super().__init__(*args, **kwargs)

        if room_id:
            self.fields['bed'].queryset = Bed.objects.filter(room_id=room_id, status='available')