from django import forms
from .models import Register, ReferralCode
from .models import AddressType, UserAddress, Customer
from django.contrib.auth.forms import SetPasswordForm
from allauth.socialaccount.forms import SignupForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class CustomSocialSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        Customer.objects.get_or_create(user=user)
        
        from .models import ReferralCode
        ReferralCode.objects.get_or_create(
            user=user,
            defaults={'code': ReferralCode.generate_unique_code(user)}
        )
        return user


class SignUpForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Password'
    }))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Confirm Password'
    }))
    
    referral_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Referral Code (Optional)',
            'style': 'text-transform: uppercase;'
        }),
        help_text='Enter a referral code to get rewards'
    )

    class Meta:
        model = Register
        fields = ('full_name', 'email', 'password', 'confirm_password', 'referral_code')
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Full Name' 
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Email ID'
            }),
        }
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password:
            try:
                validate_password(password, user=self.instance)
            except ValidationError as e:
                raise forms.ValidationError(e.messages)
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("The password doesn't match")
        return cleaned_data
    
    def clean_referral_code(self):
        """Validate referral code if provided"""
        code = self.cleaned_data.get('referral_code', '').strip().upper()
        if code:
            try:
                referral_code_obj = ReferralCode.objects.get(code=code)
                return code
            except ReferralCode.DoesNotExist:
                raise forms.ValidationError('Invalid referral code. Please check and try again.')
        return code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        
        referral_code = self.cleaned_data.get('referral_code', '').strip().upper()
        if referral_code:
            user.referred_by_code = referral_code
        
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Email ID'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Password'
    }))


class OtpVerificationForm(forms.Form):
    otp_code = forms.CharField(max_length=6, label="One-Time Password",
                               help_text="Please enter the 6-digit code sent to your email")


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Password'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Confirm Password'
        })


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
        'placeholder': 'Email ID'
    }))


class AddressTypeForm(forms.ModelForm):
    class Meta:
        model = AddressType
        fields = ['name']


class UserAddressForm(forms.ModelForm):
    class Meta:
        model = UserAddress
        fields = [ 'mobile', 'second_mob', 'address', 'city', 'state', 'pin',  'address_type', 'is_default']
        widgets = {
            'user': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '+91....'
            }),
            'second_mob': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': '+91....'
            }),
            'address': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter your full address',
                'rows': 3,   
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'State'
            }),
            'pin': forms.TextInput(attrs={  
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'PIN Code'
            }),

            'address_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-5 w-5 text-blue-600',
            }),
        }
        
class UserProfileForm(forms.ModelForm):
    
    class Meta:
        model = Customer
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
        }


class UpdateEmailForm(forms.ModelForm):
    
    class Meta:
        model = Register
        fields = ['full_name', 'email']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Full Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Email ID'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Register.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email