from django import forms
from .models import Offers
from django.core.exceptions import ValidationError
from category.models import CategoryPage
from products.models import ProductPage

class AddOfferForm(forms.ModelForm):
    
    categories = forms.ModelMultipleChoiceField(
        queryset=CategoryPage.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox h-4 w-4 text-blue-600'}),
        required=False,
        label='Select Categories'
    )
    products = forms.ModelMultipleChoiceField(
        queryset=ProductPage.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox h-4 w-4 text-blue-600'}),
        required=False,
        label='Select Products'
    )

    # Referral fields
    fixed_discount_amount = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False, initial=0,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'placeholder': 'Fixed bonus amount'})
    )
    percentage_discount = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False, initial=0,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'placeholder': 'Percentage bonus'})
    )
    validity_days = forms.IntegerField(
        required=False, initial=30,
        widget=forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'placeholder': 'Validity days'})
    )

    class Meta:
        model = Offers
        fields = [
            'name', 'description', 'offer_type', 'discount_percent',
            'fixed_discount_amount', 'percentage_discount', 'validity_days',
            'start_date', 'end_date', 'active', 'categories', 'products'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-md'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'rows': 3}),
            'offer_type': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-md'}),
            'discount_percent': forms.NumberInput(attrs={'class': 'w-full px-4 py-2 border rounded-md', 'step': '0.01', 'min': 0, 'max': 100}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-2 border rounded-md'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'w-full px-4 py-2 border rounded-md'}),
            'active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600'})
        }

    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        categories = cleaned_data.get('categories')
        products = cleaned_data.get('products')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        fixed = cleaned_data.get('fixed_discount_amount') or 0
        percent = cleaned_data.get('percentage_discount') or 0
        validity = cleaned_data.get('validity_days') or 0

        # Category / Product validation
        if offer_type == 'category' and not categories:
            raise ValidationError('Please select at least one category for category offer.')
        if offer_type == 'product' and not products:
            raise ValidationError('Please select at least one product for product offer.')

        # Referral validation
        if offer_type == 'referral' and fixed <= 0 and percent <= 0:
            raise ValidationError('For referral offer, either fixed amount or percentage bonus must be greater than 0.')
        if offer_type == 'referral' and validity <= 0:
            raise ValidationError('Validity days must be greater than 0.')

        # Date validation
        if start_date and end_date and start_date >= end_date:
            raise ValidationError('End date must be after start date.')

        return cleaned_data
