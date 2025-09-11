from django import forms
from .models import CategoryPage,OrderDetails
from products.models import ProductPage




class OrderViewForm(forms.ModelForm):
    
    
    class Meta:
        model = OrderDetails
        fields = ['order_info','order_status']
        widgets={
                "order_status": forms.Select(attrs={'class':"w-full px-4 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"}),
                

            
        }   