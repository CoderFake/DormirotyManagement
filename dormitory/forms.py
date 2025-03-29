from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Building, RoomType, Room, Bed, Amenity, RoomAmenity


class BuildingForm(forms.ModelForm):
    """Form tòa nhà ký túc xá"""

    class Meta:
        model = Building
        fields = ['name', 'code', 'address', 'floors', 'description', 'is_active', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'floors': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class RoomTypeForm(forms.ModelForm):
    """Form loại phòng"""

    class Meta:
        model = RoomType
        fields = [
            'name', 'code', 'capacity', 'area', 'amenities',
            'price_per_month', 'deposit', 'description',
            'gender_allowed', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'amenities': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'deposit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'gender_allowed': forms.Select(attrs={'class': 'form-select'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class RoomForm(forms.ModelForm):
    """Form phòng ký túc xá"""

    class Meta:
        model = Room
        fields = [
            'building', 'room_type', 'room_number', 'floor',
            'status', 'current_occupancy', 'description',
            'is_active', 'image'
        ]
        widgets = {
            'building': forms.Select(attrs={'class': 'form-select'}),
            'room_type': forms.Select(attrs={'class': 'form-select'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'floor': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'current_occupancy': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        room_type = cleaned_data.get('room_type')
        current_occupancy = cleaned_data.get('current_occupancy')

        if room_type and current_occupancy is not None:
            if current_occupancy > room_type.capacity:
                raise forms.ValidationError(_('Số người hiện tại không thể vượt quá sức chứa của loại phòng.'))

        return cleaned_data


class BedForm(forms.ModelForm):
    """Form giường"""

    class Meta:
        model = Bed
        fields = ['room', 'bed_number', 'status', 'description', 'is_active']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'bed_number': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        bed_number = cleaned_data.get('bed_number')

        if room and bed_number:
            # Kiểm tra xem số giường đã tồn tại trong phòng chưa
            if Bed.objects.filter(room=room, bed_number=bed_number).exists():
                if self.instance and self.instance.pk and self.instance.room == room and self.instance.bed_number == bed_number:
                    # Nếu đó là chính mình (đang cập nhật), bỏ qua
                    pass
                else:
                    raise forms.ValidationError(_('Số giường này đã tồn tại trong phòng.'))

        return cleaned_data


class AmenityForm(forms.ModelForm):
    """Form tiện nghi"""

    class Meta:
        model = Amenity
        fields = ['name', 'description', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
        }


class RoomAmenityForm(forms.ModelForm):
    """Form liên kết phòng và tiện nghi"""

    class Meta:
        model = RoomAmenity
        fields = ['room', 'amenity', 'quantity', 'notes']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'amenity': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class RoomFilterForm(forms.Form):
    """Form lọc phòng"""

    building = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        required=False,
        empty_label="-- Tất cả tòa nhà --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    room_type = forms.ModelChoiceField(
        queryset=RoomType.objects.all(),
        required=False,
        empty_label="-- Tất cả loại phòng --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    floor = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Tầng'})
    )

    STATUS_CHOICES = (
                         ('', '-- Tất cả trạng thái --'),
                     ) + Room.STATUS_CHOICES

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    is_active = forms.ChoiceField(
        choices=(
            ('', '-- Tất cả --'),
            ('true', 'Đang hoạt động'),
            ('false', 'Không hoạt động')
        ),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class BulkRoomCreateForm(forms.Form):
    """Form tạo nhiều phòng cùng lúc"""

    building = forms.ModelChoiceField(
        queryset=Building.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    room_type = forms.ModelChoiceField(
        queryset=RoomType.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    floor = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1})
    )

    start_number = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label=_('Số phòng bắt đầu')
    )

    end_number = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label=_('Số phòng kết thúc')
    )

    room_prefix = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_('Tiền tố phòng (không bắt buộc)')
    )

    def clean(self):
        cleaned_data = super().clean()
        start_number = cleaned_data.get('start_number')
        end_number = cleaned_data.get('end_number')

        if start_number and end_number and start_number > end_number:
            raise forms.ValidationError(_('Số phòng bắt đầu không thể lớn hơn số phòng kết thúc.'))

        return cleaned_data


class BulkBedCreateForm(forms.Form):
    """Form tạo nhiều giường cùng lúc"""

    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        label=_('Số lượng giường')
    )

    bed_prefix = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label=_('Tiền tố giường (không bắt buộc)')
    )

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        quantity = cleaned_data.get('quantity')

        if room and quantity:
            room_type = room.room_type
            existing_beds = Bed.objects.filter(room=room).count()
            total_beds = existing_beds + quantity

            if total_beds > room_type.capacity:
                raise forms.ValidationError(_(
                    'Tổng số giường (hiện tại + mới) không thể vượt quá sức chứa của loại phòng (%(capacity)s).'
                ) % {'capacity': room_type.capacity})

        return cleaned_data