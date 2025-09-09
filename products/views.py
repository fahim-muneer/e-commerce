from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.views.generic import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from .forms import ProductForm,ProductPage




class ProductView(View):
    def get(self, request):
        products =ProductPage.objects.all() # pylint: disable=no-member
        
        return render(request , 'product/product_view.html',{'products': products })
    
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
