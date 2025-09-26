from django.shortcuts import render,redirect
from django.views import View
from django.views.generic import UpdateView,DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import CategoryForm
from category.models import CategoryPage
from django.core.paginator import Paginator

class Category(View):
    def get(self , request):
        search = request.GET.get("q")
        if search:
            category=CategoryPage.objects.filter(name__icontains=search)   # pylint: disable=no-member
        else:
            category = CategoryPage.objects.all() #pylint: disable=no-member
        page = 1
        if request.GET:
            page = request.GET.get('page', 1)

        user_paginator = Paginator(category, 5)
        category = user_paginator.get_page(page)
        return render(request ,'category/category_view.html',{'category':category})



class CategoryAdd(View):
    def get(self,request):
        form=CategoryForm()
        return render(request , 'category/category_add.html',{'form':form})
    
    
    def post(self , request):
        form = CategoryForm(request.POST,request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request,'The category was successfully added.')
            return redirect('category_list')
        messages.error(request,'Invalid name. Please type valid name.')
        return render(request ,'category/category_add.html',{'form':form})



class UpdateCategory(UpdateView):
    model=CategoryPage
    fields = ['name','image']
    template_name = 'category/update_category.html'
    success_url=reverse_lazy('category_list')
    
    
class DeleteCategory(DeleteView):
    model = CategoryPage
    template_name = 'category/delete_category.html'
    success_url=reverse_lazy('category_list')