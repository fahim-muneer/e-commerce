from django import forms
from .models import Coupons
from django.utils import timezone

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupons
        fields = [
            'coupon_code', 
            'description', 
            'discount_type',
            'discount_value',
            'max_discount_amount',
            'min_cart_value', 
            'expire_at', 
            'use_limit_per_user',
            'active'
        ]
        widgets = {
            'expire_at': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'active': forms.CheckboxInput(attrs={'class': "w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"}),
        }

    def clean_discount_value(self):
        discount = self.cleaned_data.get('discount_value')
        discount_type = self.cleaned_data.get('discount_type')
        
        if discount is not None and discount <= 0:
            raise forms.ValidationError("Discount value must be greater than 0.")
        
        if discount_type == 'percentage' and discount > 100:
            raise forms.ValidationError("Percentage discount cannot exceed 100%.")
        
        return discount

    def clean_expire_at(self):
        expire_at = self.cleaned_data.get('expire_at')
        if expire_at and expire_at < timezone.now().date():
            raise forms.ValidationError("The expiry date cannot be in the past.")
        return expire_at

    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            code = code.upper()  
            if not code.replace('_', '').replace('-', '').isalnum():
                raise forms.ValidationError("Coupon code should contain only letters, numbers, hyphens and underscores.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        min_cart_value = cleaned_data.get('min_cart_value')
        discount_value = cleaned_data.get('discount_value')
        discount_type = cleaned_data.get('discount_type')

        if discount_type == 'fixed' and min_cart_value and discount_value:
            if discount_value >= min_cart_value:
                raise forms.ValidationError(
                    "Fixed discount amount cannot be greater than or equal to the minimum cart value."
                )

        return cleaned_data
