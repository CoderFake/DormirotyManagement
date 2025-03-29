from django import forms
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from dormitory.models import Building, Room
from .models import MaintenanceCategory, MaintenanceRequest, MaintenanceComment


class MaintenanceCategoryForm(forms.ModelForm):
    """Form danh mục bảo trì"""

    class Meta:
        model = MaintenanceCategory
        fields = ['name', 'description', 'is_active', 'icon', 'average_time']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'icon': forms.TextInput(attrs={'class': 'form-control'}),
            'average_time': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class MaintenanceRequestForm(forms.ModelForm):
    """Form yêu cầu bảo trì (cho sinh viên)"""

    # Instead of using multiple=True, we'll handle multiple file uploads in the view
    images = forms.ImageField(
        label=_('Hình ảnh'),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = MaintenanceRequest
        fields = ['category', 'title', 'description', 'priority', 'room']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select', 'readonly': True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].widget = forms.HiddenInput()


class MaintenanceRequestAdminForm(forms.ModelForm):
    """Form yêu cầu bảo trì (cho Admin)"""
    images = forms.ImageField(
        label=_('Hình ảnh'),
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = MaintenanceRequest
        fields = [
            'category', 'title', 'description', 'priority', 'room', 'building',
            'status', 'scheduled_date', 'assigned_to', 'admin_notes'
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'room': forms.Select(attrs={'class': 'form-select'}),
            'building': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(
            user_type__in=['staff', 'admin'], is_active=True
        ).order_by('full_name')


class MaintenanceAssignForm(forms.Form):
    """Form phân công xử lý yêu cầu bảo trì"""

    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type__in=['staff', 'admin'], is_active=True).order_by('full_name'),
        label=_('Phân công cho'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    scheduled_date = forms.DateTimeField(
        label=_('Ngày xử lý dự kiến'),
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control datetimepicker'})
    )

    notes = forms.CharField(
        label=_('Ghi chú'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )


class MaintenanceCommentForm(forms.ModelForm):
    """Form bình luận về yêu cầu bảo trì"""

    class Meta:
        model = MaintenanceComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Nhập bình luận của bạn...'}),
        }