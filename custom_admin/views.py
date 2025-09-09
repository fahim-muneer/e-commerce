from django.shortcuts import render,redirect,get_object_or_404
from django.views import View
from django.views.generic.edit import UpdateView,DeleteView
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm

User = get_user_model()

# Create your views here.

class LoginAdmin(View):
    def get(self, request):
        
        
        if request.user.is_authenticated:
            return redirect('dashboard')
        
        
        form = AdminLoginForm()
        
        return render(request, 'custom_admin/admin_login.html',{'form':form})

    def post(self, request):
        
        form = AdminLoginForm(request.POST)
        
        if form.is_valid():
            
        
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request , username = email , password = password )
            
            if user is not None:
                login(request,user)
                messages.success(request , "You are Successfully loged in.")
                return redirect('dashboard')
            
            messages.error(request , "The admin is not registered.")
            return redirect('login')
        
        messages.error(request , "Invalid credentials.")
        return render(request ,'custom_admin/admin_login.html',{'form': form})
                


def log_out(request):
    logout(request)
    return redirect('admin_login')

class DashBoard(View):
    def get(self, request):
        return render(request, 'custom_admin/dashboard.html')