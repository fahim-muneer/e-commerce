from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.views.generic.edit import UpdateView,DeleteView
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm
from customer.models import Register
from django.db.models import Count
from orders.models import Cart,Orders,OrderItem
from products.models import ProductPage
from category.models import CategoryPage
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.contrib.admin.views.decorators import staff_member_required
User = get_user_model()

class AdminLoginMixin(LoginRequiredMixin):
    login_url = '/custom_admin/'
    redirect_field_name = 'next'


class LoginAdmin(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('dashboard')
            else:
                return redirect('home') 
        
        form = AdminLoginForm()
        return render(request, 'custom_admin/admin_login.html', {'form': form})
            
            

    def post(self, request):
        
        form = AdminLoginForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if not user.is_superuser:
                    messages.error(request, "You don't have admin privileges.")
                    return render(request, 'custom_admin/admin_login.html', {'form': form})
                
                login(request, user)
                
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid credentials.")
        
        return render(request, 'custom_admin/admin_login.html', {'form': form})

@never_cache
def log_out(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            logout(request)
            return redirect('admin_login')
        else:
           
            return redirect('home')
    return redirect('admin_login')


@method_decorator(never_cache, name='dispatch')
class DashBoard(AdminLoginMixin,View):
    def get(self, request):
        total_user=Register.objects.aggregate(total=Count("id"))['total']
        total_orders=Orders.objects.aggregate(total=Count("id"))['total']          #pylint: disable=no-member
        total_products=ProductPage.objects.aggregate(total=Count("id"))['total']  #pylint: disable=no-member
        total_category=CategoryPage.objects.aggregate(total=Count("id"))['total']   #pylint: disable=no-member
        
        context={
            'total_user': total_user,
            'total_orders' : total_orders,
            'total_products':total_products,
            'total_category':total_category
        }
        
        return render(request, 'custom_admin/dashboard.html',context)
    
