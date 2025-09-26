from django import forms
from .models import Register
from .models import AddressType, UserAddress , Customer
from django.contrib.auth.forms import SetPasswordForm
from allauth.socialaccount.forms import SignupForm



class CustomSocialSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        Customer.objects.get_or_create(user=user)   #pylint: disable=no-member
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

    class Meta:
        model = Register
        fields = ('full_name', 'email', 'password')
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

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("The password doesn't match")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
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
        fields = [ 'mobile', 'second_mob', 'address', 'city', 'state', 'pin', 'country', 'address_type', 'is_default']
        widgets = {
            'user': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Mobile Number'
            }),
            'second_mob': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Second Mobile Number'
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
            'country': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Country'
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
            model=Register
            fields=['full_name','email']
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