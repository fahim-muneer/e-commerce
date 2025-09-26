from django.shortcuts import render,redirect
from django.views import View
from django.views.generic import UpdateView,DeleteView
from .forms import VarientsForm
from .models import Varients
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator


# Create your views here.
class VarientsView(View):
    def get(self,request):
        search = request.GET.get("q")
        if search:
            varient=Varients.objects.filter(name__icontains=search)   # pylint: disable=no-member
        else:
            varient = Varients.objects.all() #pylint: disable=no-member
        page = 1
        if request.GET:
            page = request.GET.get('page', 1)

        user_paginator = Paginator(varient, 5)
        varient = user_paginator.get_page(page)
        
     
        context={
            'varient':varient
                }
        return render (request, 'varients/varients.html',context)



class AddVarients(View):
    def get(self , request):
        form=VarientsForm()
        return render(request ,'varients/add_varients.html',{'form':form})
    def post(self , request):
        form =VarientsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,'The varient is added successfully.')
            return redirect('varient_list')
        else:
            messages.error(request,'Check your credentials.The varient is not added.')
            return render(request,'varients/varients.html',{'form':form})


class UpdateVarients(UpdateView):
    model=Varients
    fields=['name']
    template_name='varients/update_varients.html'
    success_url=reverse_lazy('varient_list')

class DeleteVarients(DeleteView):
    models=Varients
    template_name='varients/delete_varients.html'
    success_url=reverse_lazy('varient_list')
    

