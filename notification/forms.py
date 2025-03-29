from django import forms
from django.utils.translation import gettext_lazy as _
from .models import NotificationCategory, Notification, Announcement


class NotificationCategoryForm(forms.ModelForm):
    """Form danh mục thông báo"""

    class Meta:
        model = NotificationCategory
        fields = ['name', 'description', 'color', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'color': forms.Select(attrs={'class': 'form-select'}, choices=[
                ('primary', 'Xanh dương'),
                ('secondary', 'Xám'),
                ('success', 'Xanh lá'),
                ('danger', 'Đỏ'),
                ('warning', 'Vàng'),
                ('info', 'Xanh nhạt'),
                ('dark', 'Đen'),
            ]),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NotificationForm(forms.ModelForm):
    """Form thông báo"""

    user_target = forms.ChoiceField(
        label=_('Đối tượng nhận'),
        choices=[
            ('all', 'Tất cả người dùng'),
            ('students', 'Tất cả sinh viên'),
            ('staff', 'Tất cả nhân viên'),
            ('building', 'Theo tòa nhà'),
            ('room', 'Theo phòng'),
            ('specific', 'Người dùng cụ thể'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    specific_users = forms.ModelMultipleChoiceField(
        label=_('Người dùng cụ thể'),
        queryset=None,
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select searchable-select', 'size': '5'})
    )

    class Meta:
        model = Notification
        fields = [
            'title', 'content', 'category', 'priority',
            'start_date', 'end_date', 'is_active', 'is_global',
            'target_buildings', 'target_rooms'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_global': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'target_buildings': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'target_rooms': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }

    def __init__(self, *args, **kwargs):
        from accounts.models import User
        super().__init__(*args, **kwargs)
        self.fields['specific_users'].queryset = User.objects.filter(is_active=True).order_by('full_name')


class AnnouncementForm(forms.ModelForm):
    """Form thông báo chung"""

    class Meta:
        model = Announcement
        fields = ['title', 'content', 'is_active', 'start_date', 'end_date', 'is_pinned', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }