from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from customer.models import Customer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model

User = get_user_model()


class UserPanel(View):
    def get(self, request):
        search = request.GET.get("q")
        if search:
            user=Customer.objects.filter(user__full_name__icontains=search)   # pylint: disable=no-member
        else:
            user = Customer.objects.all()  # pylint: disable=no-member
        user = user.exclude(user__is_superuser=True)
        page = 1
        if request.GET:
            page = request.GET.get('page', 1)

        user_paginator = Paginator(user, 5)
        user = user_paginator.get_page(page)

        return render(request, 'user_panel/user_panel.html', {'user': user})


class DeleteUser(View):
    def post(self, request):
        selected_id = request.POST.getlist("selected_users")
        if selected_id:
            User.objects.filter(id__in=selected_id).delete()
            messages.success(request, f'Deleted {len(selected_id)} users successfully.')
        else:
            messages.error(request, 'No users were selected.')
        return redirect("user_panel")
    
    
    
    def logout_user(self, user):
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session.delete()


class BloackUser(LoginRequiredMixin, View):
    
    login_url = 'login'
    redirect_field_name = 'next'
    
    def post(self, request, uid):
        user = get_object_or_404(User, pk=uid)
        if user.is_active:
            user.is_active = False
            
        else:
            user.is_active = True
           
            
        user.save()
        return redirect('user_panel')

    def logout_user(self, user):
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        for session in sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user.id):
                session.delete()


