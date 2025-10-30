from django.shortcuts import render,redirect
from .models import Banner
from django.views import View
from django.views.generic import UpdateView,DeleteView
from .forms import BannerForm
from django.urls import reverse_lazy
from django.core.paginator import Paginator

class BannerView(View):
    def get(self, request):
        try:
            banner = Banner.objects.all()
            page = request.GET.get('page', 1)
            user_paginator = Paginator(banner, 5)
            banner = user_paginator.get_page(page)
            return render(request, 'banner/banner_view.html', {'banner': banner})
        except Exception as e:
            print(f"The error is {str(e)}")
            return render(request, 'banner/banner_view.html', {'banner': []})  


class AddBanner(View):
    def get(self, request):
        form = BannerForm()
        return render(request, 'banner/add_banner.html', {'form': form})
    
    def post(self, request):
        form = BannerForm(request.POST, request.FILES)  
        try:
            if form.is_valid():
                form.save()
                return redirect('banner_view')
            else:
                print(f"Form errors: {form.errors}")
                return render(request, 'banner/add_banner.html', {'form': form})
        except Exception as e:
            print(f"Got error in the form validations: {str(e)}")
            return render(request, 'banner/add_banner.html', {'form': form})

class EditBanner(UpdateView):
    model=Banner
    fields=['name','image']
    template_name='banner/edit_banner.html'
    success_url = reverse_lazy('banner_view')


class DeleteBanner(DeleteView):
    model=Banner
    template_name='banner/delete_banner.html'
    success_url=reverse_lazy('banner_view')
