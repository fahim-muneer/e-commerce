from django import forms
from .models import CategoryPage,CartItems,OrderAddress,Orders
from products.models import ProductPage


     
class CartForms(forms.ModelForm):
    
    class Meta:
        model =CartItems
        fields=['product','quantity','owner']

        
class OrderAddressForm(forms.ModelForm):
    
    class Meta:
        model = OrderAddress
        fields = ['mobile','second_mob','address','city','state','pin','country',]
        widgets = {
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
        }