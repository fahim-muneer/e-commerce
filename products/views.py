from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.views.generic import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from category.models import CategoryPage
from .forms import ProductForm,ProductPage
from wish_list.models import WishListItems
from varients.models import Varients




class ProductView(View):
    def get(self, request):
        filter = request.GET.get("category")
        search= request.GET.get("q")
        
        
        products =ProductPage.objects.all() # pylint: disable=no-member
        wishlist_ids = []

        if request.user.is_authenticated:
            wishlist_ids = WishListItems.objects.filter(wish_list__user=request.user).values_list('products_id', flat=True) # pylint: disable=no-member
        
        if filter and filter != 'All Categories':
            products = products.filter(category__name__icontains=filter)
            
        if search:
            products=ProductPage.objects.filter(icontains=search)   # pylint: disable=no-member

        
        page = request.GET.get('page', 1)

        product_paginator = Paginator(products, 40)
        products = product_paginator.get_page(page)
        
        context={
            'products': products,
            'wishlist_ids':wishlist_ids,
            'categories': CategoryPage.objects.all(),   # pylint: disable=no-member
            'varient':Varients.objects.all()            # pylint: disable=no-member  
        }
        return render(request, 'product/product_view.html', context)  



class ProductAdding(View):
    def get(self, request):
        context = {
            'form': ProductForm()  
        }
        return render(request, 'product/product_add.html', context)
    
    def post(self, request):
        form = ProductForm(request.POST, request.FILES) 
        
        if form.is_valid():
            form.save()
            messages.success(request, "The product was added successfully.")
            return redirect('product_list')
        
        else:
            messages.error(request, 'Value error, please check the data and try again.')
            context = {
                'form': form
            }
           
            return render(request, 'product/product_add.html', context)
    
    
    
    
class ProductUpdate(UpdateView):
    model = ProductPage
    fields = ['image1','image2','image3','image4','image5','name','description','category','price','old_price','block','stock']
    template_name ='product/update_product.html'
    success_url = reverse_lazy('product_list')
    
class ProductDelete(DeleteView):
    model = ProductPage
    template_name='product/delete_product.html'
    success_url=reverse_lazy('product_list')



class ProductDetail(View):
    def get(self , request,pk):
        obj = get_object_or_404(ProductPage,pk=pk)
        context={
            'obj': obj
        }
        return render (request , 'product/product_detail.html',context)





# Create your views here.
