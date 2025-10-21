from django import forms
from .models import Coupons
from django.utils import timezone

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupons
        fields = [
            'coupon_code',
            'description',
            'min_cart_value',
            'discount_value',
            'expire_at',
            'use_limit',
            'active',
        ]
        widgets = {
            # 'expire_at': forms.DateInput(attrs={'type': 'date'}),
            # 'description': forms.Textarea(attrs={'rows': 2, 'class': 'w-full rounded-md border border-gray-300 p-2'}),
            # 'coupon_code': forms.TextInput(attrs={'class': 'w-full rounded-md border border-gray-300 p-2'}),
            # 'min_cart_value': forms.NumberInput(attrs={'class': 'w-full rounded-md border border-gray-300 p-2'}),
            # 'discount_value': forms.NumberInput(attrs={'class': 'w-full rounded-md border border-gray-300 p-2'}),
            # 'use_limit': forms.NumberInput(attrs={'class': 'w-full rounded-md border border-gray-300 p-2'}),
            'active': forms.CheckboxInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
        }

    def clean_discount_value(self):
        discount = self.cleaned_data.get('discount_value')
        if discount is not None and (discount <= 0 or discount > 100):
            raise forms.ValidationError("Discount value must be between 1 and 100.")
        return discount

    def clean_expire_at(self):
        expire_at = self.cleaned_data.get('expire_at')
        if expire_at and expire_at < timezone.now().date():
            raise forms.ValidationError("The expiry date cannot be in the past.")
        return expire_at

    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code and not code.isalnum():
            raise forms.ValidationError("Coupon code should contain only letters and numbers.")
        return code
