from django import forms
from .models import ProductPage


class ProductForm(forms.ModelForm):
    
    
    class Meta:
        model = ProductPage
        fields = ['image1','image2','image3','image4','image5','name','description','category','price','old_price','block','stock',]
        widgets={
            "image1": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "image2": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "image3": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "image4": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "image5": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),

            "name": forms.TextInput (attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "description": forms.Textarea(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500", 'rows': 4}),
            "category": forms.Select(attrs={'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "price": forms.NumberInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "old_price": forms.NumberInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "block": forms.CheckboxInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            "stock": forms.NumberInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            # "created_at":forms.DateInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
            
        }