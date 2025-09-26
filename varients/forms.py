from django import forms
from .models import Varients


class VarientsForm(forms.ModelForm):
    
    class Meta:
        model=Varients
        fields=['name']
        widgets={
        "name": forms.TextInput (attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),

        }
