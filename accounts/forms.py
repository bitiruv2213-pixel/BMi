from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from .models import Profile


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True, label="Ism")
    last_name = forms.CharField(max_length=50, required=True, label="Familiya")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class UserLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parol'})
    )


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'username': 'Foydalanuvchi nomi',
            'email': 'Email',
            'first_name': 'Ism',
            'last_name': 'Familiya',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'phone', 'birth_date', 'location', 'website',
                  'github', 'telegram', 'linkedin']
        labels = {
            'avatar': 'Rasm',
            'bio': 'Bio (o\'zingiz haqingizda)',
            'phone': 'Telefon raqam',
            'birth_date': 'Tug\'ilgan sana',
            'location': 'Manzil',
            'website': 'Veb-sayt',
            'github': 'GitHub',
            'telegram': 'Telegram',
            'linkedin': 'LinkedIn',
        }
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+998 90 123 45 67'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Toshkent, O\'zbekiston'}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com'}),
            'github': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
            'telegram': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '@username'}),
            'linkedin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'email@example.com',
        'autofocus': True,
    }))


class PasswordResetCodeConfirmForm(forms.Form):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'email@example.com',
    }))
    code = forms.CharField(
        label="Tasdiqlash kodi",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '123456',
            'inputmode': 'numeric',
            'autocomplete': 'one-time-code',
        }),
    )
    new_password1 = forms.CharField(label="Yangi parol", widget=forms.PasswordInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Yangi parol',
    }))
    new_password2 = forms.CharField(label="Parolni tasdiqlang", widget=forms.PasswordInput(attrs={
        'class': 'form-control form-control-lg',
        'placeholder': 'Parolni qayta kiriting',
    }))

    def clean_code(self):
        return ''.join(ch for ch in self.cleaned_data['code'] if ch.isdigit())

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', "Parollar mos emas.")

        if password1:
            try:
                validate_password(password1)
            except forms.ValidationError as exc:
                self.add_error('new_password1', exc)

        return cleaned_data
