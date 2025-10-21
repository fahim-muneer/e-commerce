from django import forms
from .models import CategoryPage
from django.core.exceptions import ValidationError




class CategoryForm(forms.ModelForm):
    
    class Meta:
        model = CategoryPage
        fields = ['name','image']
        widgets={ "name": forms.TextInput (attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
                  "image": forms.FileInput(attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),

                
                }
