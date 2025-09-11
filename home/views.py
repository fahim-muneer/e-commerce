from django.shortcuts import render
from products.models import ProductPage
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.views.generic import DetailView,View
from products.models import ProductPage
from category.models import CategoryPage
User = get_user_model()

# Create your views here.
class Index(View):
    def get(self,request):
        latest_products=ProductPage.objects.order_by('-pk')[:5]   #pylint: disable=no-member
        featured_product=ProductPage.objects.order_by('priority')[:5] #pylint: disable=no-member
        popular_product=ProductPage.objects.order_by('price')[:10] #pylint: disable=no-member
        category = CategoryPage.objects.all()[:4]  #pylint: disable=no-member
        context={
            'latest_products': latest_products,
            'featured_product':featured_product,
            'popular_product':popular_product,
            'category':category
            
        }
        return render(request, 'home/index.html',context)
        

def home(request):
    
    
    products = ProductPage.objects.all()  # pylint: disable=no-member
    page=1
    if request.GET:
        page = request.GET.get('page',1)
    
    product_paginator = Paginator(products,40)
    products = product_paginator.get_page(page)
    return render(request,'home/home.html',{'products':products})

        
class ProdectDetails(DetailView):
    model=ProductPage
    fields=['image1','image2','image3','image4','image5','name','description','price','old_price','category']
    template_name='home/product_details_page.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.get_object()

        related_products = ProductPage.objects.filter(     #pylint: disable=no-member
            category=product.category
        ).exclude(id=product.id)[:4]

        context["related_products"] = related_products
        return context


