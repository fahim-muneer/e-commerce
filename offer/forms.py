from django import forms
from .models import Offers
from django.core.exceptions import ValidationError

from category.models import CategoryPage
from products.models import ProductPage

class AddOfferForm(forms.ModelForm):
    # Add custom fields for selecting categories/products
    categories = forms.ModelMultipleChoiceField(
        queryset=CategoryPage.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600'
        }),
        required=False,
        label='Select Categories'
    )
    
    products = forms.ModelMultipleChoiceField(
        queryset=ProductPage.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600'
        }),
        required=False,
        label='Select Products'
    )
    
    class Meta:
        model = Offers
        fields = ['name', 'description', 'offer_type', 'discount_percent', 
                  'start_date', 'end_date', 'active', 'categories', 'products']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter offer name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter offer description',
                'rows': 3
            }),
            'offer_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'onchange': 'toggleOfferFields(this.value)'
            }),
            'discount_percent': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter discount percentage',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500',
                'type': 'datetime-local'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        offer_type = cleaned_data.get('offer_type')
        categories = cleaned_data.get('categories')
        products = cleaned_data.get('products')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # Validate based on offer type
        if offer_type == 'category' and not categories:
            raise ValidationError('Please select at least one category for category offer.')
        
        if offer_type == 'product' and not products:
            raise ValidationError('Please select at least one product for product offer.')
        
        # Validate dates
        if start_date and end_date and start_date >= end_date:
            raise ValidationError('End date must be after start date.')
        
        return cleaned_data
