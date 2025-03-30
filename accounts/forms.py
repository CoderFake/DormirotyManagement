from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, SetPasswordForm, \
    PasswordChangeForm
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile


class UserLoginForm(AuthenticationForm):
    """Form đăng nhập tùy chỉnh"""

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Nhập email của bạn'})
    )
    password = forms.CharField(
        label=_("Mật khẩu"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu'})
    )

    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    error_messages = {
        'invalid_login': _(
            "Vui lòng nhập đúng email và mật khẩu. Lưu ý rằng cả hai trường đều phân biệt chữ hoa chữ thường."
        ),
        'inactive': _("Tài khoản này đã bị vô hiệu hóa."),
    }

    class Meta:
        model = User
        fields = ('username', 'password', 'remember_me')


class UserRegistrationForm(UserCreationForm):
    """Form đăng ký người dùng tùy chỉnh"""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Nhập email của bạn'})
    )
    full_name = forms.CharField(
        label=_("Họ và tên"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên đầy đủ'})
    )
    student_id = forms.CharField(
        label=_("Mã sinh viên"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mã sinh viên'})
    )
    phone_number = forms.CharField(
        label=_("Số điện thoại"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập số điện thoại'})
    )
    password1 = forms.CharField(
        label=_("Mật khẩu"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu'}),
    )
    password2 = forms.CharField(
        label=_("Xác nhận mật khẩu"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu'}),
    )
    agree_terms = forms.BooleanField(
        required=True,
        label=_("Tôi đồng ý với Điều khoản sử dụng và Chính sách bảo mật"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    gender = forms.ChoiceField(
        label=_("Giới tính"),
        choices=User.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    date_of_birth = forms.DateField(
        label=_("Ngày sinh"),
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control datepicker', 'placeholder': 'DD/MM/YYYY'})
    )
    id_card_number = forms.CharField(
        label=_("Số CMND/CCCD"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập số CMND/CCCD'})
    )
    university = forms.CharField(
        label=_("Trường đại học"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên trường đại học'})
    )
    faculty = forms.CharField(
        label=_("Khoa"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập tên khoa'})
    )

    class Meta:
        model = User
        fields = (
            'email', 'full_name', 'student_id', 'phone_number', 'gender', 'date_of_birth',
            'id_card_number', 'university', 'faculty', 'password1', 'password2', 'agree_terms'
        )

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('agree_terms'):
            raise forms.ValidationError(_("Bạn phải đồng ý với điều khoản và chính sách để tiếp tục."))

        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Mật khẩu xác nhận không khớp."))

        date_of_birth = cleaned_data.get('date_of_birth')
        if date_of_birth:
            import datetime
            age = (datetime.date.today() - date_of_birth).days / 365.25
            if age < 16:
                raise forms.ValidationError(_("Bạn phải từ 16 tuổi trở lên để đăng ký."))

        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError(_("Email là bắt buộc."))

        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        if not re.match(email_regex, email):
            raise forms.ValidationError(_("Địa chỉ email không hợp lệ."))

        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get('student_id').upper()

        if not student_id:
            raise forms.ValidationError(_("Mã sinh viên là bắt buộc."))

        import re
        student_id_regex = r'^[A-Z]\d{2}[A-Z]{4}\d{3}'

        if not re.match(student_id_regex, student_id):
            raise forms.ValidationError(_("Mã sinh viên không đúng định dạng. Ví dụ: B21DCCN123"))

        return student_id


    def clean_id_card_number(self):
        id_card_number = self.cleaned_data.get('id_card_number')
        if not id_card_number:
            raise forms.ValidationError(_("Số CMND/CCCD là bắt buộc."))

        if not (len(id_card_number) == 9 or len(id_card_number) == 12):
            raise forms.ValidationError(_("Số CMND/CCCD phải có 9 hoặc 12 chữ số."))

        if not id_card_number.isdigit():
            raise forms.ValidationError(_("Số CMND/CCCD chỉ được chứa các chữ số."))

        return id_card_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number:
            raise forms.ValidationError(_("Số điện thoại là bắt buộc."))

        import re
        phone_regex = r'^(0[3|5|7|8|9])+([0-9]{8})'

        if not re.match(phone_regex, phone_number):
            raise forms.ValidationError(_("Số điện thoại không đúng định dạng. Ví dụ: 0387367162"))

        return phone_number

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get('date_of_birth')
        if not date_of_birth:
            raise forms.ValidationError(_("Ngày sinh là bắt buộc."))

        import datetime
        today = datetime.date.today()
        age = (today - date_of_birth).days / 365.25

        if age < 16:
            raise forms.ValidationError(_("Bạn phải từ 16 tuổi trở lên để đăng ký."))

        if age > 100:
            raise forms.ValidationError(_("Ngày sinh không hợp lệ."))

        return date_of_birth

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None
        user.user_type = 'student'
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    """Form đặt lại mật khẩu tùy chỉnh"""

    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Nhập email của bạn'})
    )


class CustomSetPasswordForm(SetPasswordForm):
    """Form thiết lập mật khẩu mới tùy chỉnh"""

    new_password1 = forms.CharField(
        label=_("Mật khẩu mới"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Xác nhận mật khẩu mới"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu mới'}),
    )


class CustomPasswordChangeForm(PasswordChangeForm):
    """Form thay đổi mật khẩu tùy chỉnh"""

    old_password = forms.CharField(
        label=_("Mật khẩu hiện tại"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu hiện tại'}),
    )
    new_password1 = forms.CharField(
        label=_("Mật khẩu mới"),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu mới'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label=_("Xác nhận mật khẩu mới"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu mới'}),
    )


class UserProfileForm(forms.ModelForm):
    """Form chỉnh sửa thông tin người dùng"""

    class Meta:
        model = User
        fields = (
            'full_name', 'phone_number', 'gender', 'date_of_birth', 'address',
            'id_card_number', 'university', 'faculty', 'avatar'
        )
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control datepicker'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'id_card_number': forms.TextInput(attrs={'class': 'form-control'}),
            'university': forms.TextInput(attrs={'class': 'form-control'}),
            'faculty': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }


class UserProfileExtendedForm(forms.ModelForm):
    """Form thông tin bổ sung cho hồ sơ người dùng"""

    class Meta:
        model = UserProfile
        fields = (
            'parent_name', 'parent_phone', 'emergency_contact', 'emergency_phone',
            'home_town', 'bio', 'facebook_url'
        )
        widgets = {
            'parent_name': forms.TextInput(attrs={'class': 'form-control'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'home_town': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
        }


class AdminUserCreateForm(UserCreationForm):
    """Form tạo người dùng (dành cho Admin)"""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Nhập email'})
    )
    full_name = forms.CharField(
        label=_("Họ và tên"),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập họ và tên đầy đủ'})
    )
    phone_number = forms.CharField(
        label=_("Số điện thoại"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nhập số điện thoại'})
    )
    user_type = forms.ChoiceField(
        label=_("Loại người dùng"),
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    password1 = forms.CharField(
        label=_("Mật khẩu"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập mật khẩu'}),
    )
    password2 = forms.CharField(
        label=_("Xác nhận mật khẩu"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nhập lại mật khẩu'}),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Kích hoạt tài khoản"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = (
            'email', 'full_name', 'phone_number', 'user_type',
            'password1', 'password2', 'is_active'
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("Email này đã được sử dụng. Vui lòng chọn email khác."))
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = None  # Sử dụng email thay cho username
        user.is_staff = self.cleaned_data.get('user_type') in ['admin', 'staff']
        user.is_superuser = self.cleaned_data.get('user_type') == 'admin'
        if commit:
            user.save()
        return user


class AdminUserEditForm(forms.ModelForm):
    """Form chỉnh sửa người dùng (dành cho Admin)"""

    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': True})
    )
    full_name = forms.CharField(
        label=_("Họ và tên"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone_number = forms.CharField(
        label=_("Số điện thoại"),
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    user_type = forms.ChoiceField(
        label=_("Loại người dùng"),
        choices=User.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.BooleanField(
        required=False,
        label=_("Kích hoạt tài khoản"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = User
        fields = ('email', 'full_name', 'phone_number', 'user_type', 'is_active')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = self.cleaned_data.get('user_type') in ['admin', 'staff']
        user.is_superuser = self.cleaned_data.get('user_type') == 'admin'
        if commit:
            user.save()
        return user