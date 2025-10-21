from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.views.generic import UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.paginator import Paginator
from category.models import CategoryPage
from .forms import ProductForm,ProductPage,ProductVariantCrudForm
from wish_list.models import WishListItems
from varients.models import Varient
from .models import ProductVariants
from custom_admin.views import AdminLoginMixin
from django.http import JsonResponse
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import os
from django.urls import reverse


@csrf_exempt  
def upload_cropped_image(request):
    if request.method == 'POST': 
        image_file = request.FILES.get('image')
        if not image_file:
            return JsonResponse({'error': 'No image uploaded'}, status=400)

        
        save_path = os.path.join(settings.MEDIA_ROOT, 'cropped')
        os.makedirs(save_path, exist_ok=True)

        file_path = os.path.join(save_path, image_file.name)
        with open(file_path, 'wb+') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # Return the image URL
        image_url = f"{settings.MEDIA_URL}cropped/{image_file.name}"
        return JsonResponse({'image_url': image_url})

    return JsonResponse({'error': 'Invalid request method'}, status=400)




class ProductView(AdminLoginMixin,View):
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
            products=ProductPage.objects.filter(name__icontains=search)   # pylint: disable=no-member

        
        page = request.GET.get('page', 1)

        product_paginator = Paginator(products, 5)
        products = product_paginator.get_page(page)
        
        context={
            'products': products,
            'wishlist_ids':wishlist_ids,
            'categories': CategoryPage.objects.all(),   # pylint: disable=no-member
            # 'varient':Varient.objects.all()            # pylint: disable=no-member  
        }
        return render(request, 'product/product_view.html', context)  





class ProductAdding(AdminLoginMixin, View):
    def get(self, request):
        form = ProductForm()
        # Create a list of the image fields
        image_fields = [
            form['image1'],
            form['image2'],
            form['image3'],
            form['image4'],
            form['image5'],
        ]
        context = {
            'form': form,
            'image_fields': image_fields,  # This variable holds the list
        }
        return render(request, 'product/product_add.html', context)
    
    # Your post method can remain as it is if you prefer to build the context that way
    def post(self, request):
        form = ProductForm(request.POST, request.FILES) 
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Product added successfully!')
            return redirect('product_list')
        
        image_fields = [
            form['image1'],
            form['image2'],
            form['image3'],
            form['image4'],
            form['image5'],
        ]
        messages.error(request, 'Please correct the errors below and try again.')
        context = {
            'form': form,
            'image_fields': image_fields, # Pass the list to the template
        }
        return render(request, 'product/product_add.html', context)
    
class ProductUpdate(UpdateView):
    model = ProductPage
    fields = ['image1','image2','image3','image4','image5','name','description','category','priority','old_price','block']
    template_name ='product/update_product.html'
    success_url = reverse_lazy('product_list')
    
class ProductDelete(DeleteView):
    model = ProductPage
    template_name='product/delete_product.html'
    success_url=reverse_lazy('product_list')



class ProductDetail(AdminLoginMixin,View):
    def get(self , request,pk):
        product = get_object_or_404(ProductPage,pk=pk)
        variants =product.variant.all()
        context={
            'product': product,
            'variants':variants
        }
        return render (request , 'product/product_detail.html',context)



class AddProductVariant(AdminLoginMixin,View):
    def get(self,request , pid ):
        product=get_object_or_404(ProductPage,id=pid)
        variants=Varient.objects.all()  #pylint: disable=no-member
        context={
            'product':product,
            'variants':variants
        }
        return render (request,'product/add_product_variants.html',context)
    
    def post(self , request , pid ):
        product=get_object_or_404(ProductPage,id=pid)
        variants=Varient.objects.all()  #pylint: disable=no-member

        vid=request.POST.get('variant')
        stock=request.POST.get('stock')
        price=request.POST.get('price')
        
        
        variant=get_object_or_404(Varient,id=vid)  
        try:
            ProductVariants.objects.create(   #pylint: disable=no-member
            product=product,
            variant=variant,
            stock=stock,
            price=price
            
            )
            return redirect('product_list')
        except Exception as e :
            messages.error(request,f'The error is {str(e)}')
            context={
            'product':product,
            'variants':variants
            
        }
            return render (request,'product/add_product_variants.html',context)
class UpdateProductVariant(AdminLoginMixin,UpdateView):
    model=ProductVariants
    form_class=ProductVariantCrudForm
    template_name='product/update_product_variant.html'
    success_url=reverse_lazy('product_details')
    
    def get_success_url(self):
        product_id = self.object.product.id
        return reverse('product_details', kwargs={'pk': product_id})


class DeleteProductVariant(AdminLoginMixin,DeleteView):
    model=ProductVariants
    template_name="product/delete_product_variant.html"
    success_url=reverse_lazy('product_details')
    
    def get_success_url(self):
        product_id = self.object.product.id
        return reverse('product_details', kwargs={'pk': product_id})

            
    

        
        


