from django import forms
from .models import Varient


class VarientsForm(forms.ModelForm):
    
    class Meta:
        model=Varient
        fields=['name']
        widgets={
        "name": forms.TextInput (attrs={ 'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),

        }
