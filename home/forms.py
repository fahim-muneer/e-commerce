from django import forms
from products.models import ProductVariants

class VarientSelectforms(forms.Form):
    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['variant'].queryset = queryset or ProductVariants.objects.none()
        
    variant = forms.ModelChoiceField(
        queryset=ProductVariants.objects.none(),
        widget=forms.Select(
            attrs={
                "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500",
                "onchange": "this.form.submit()",
            }
        )
    )
