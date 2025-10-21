from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from .models import ProductPage, WishList, WishListItems
from customer.models import Customer





class MyList(LoginRequiredMixin, View):
    def get(self, request):
        profile = get_object_or_404(Customer, user=request.user)
        my_list, _ = WishList.objects.get_or_create(user=request.user)  # pylint: disable=no-member
        wishlist_items = WishListItems.objects.filter(wish_list=my_list)  # pylint: disable=no-member

        product_paginator = Paginator(wishlist_items, 2)
        page_number = request.GET.get('page', 1)
        wishlist_items = product_paginator.get_page(page_number)

        context = {
            'profile': profile,
            'wishlist_items': wishlist_items,
        }
        return render(request, 'wish_list/wish_list.html', context)

    def post(self, request):
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')

        if product_id and action:
            product = get_object_or_404(ProductPage, pk=product_id)
            my_list, _ = WishList.objects.get_or_create(user=request.user)   # pylint: disable=no-member

            if action == 'add':
                WishListItems.objects.get_or_create(wish_list=my_list, products=product)   # pylint: disable=no-member
            elif action == 'remove':
                WishListItems.objects.filter(wish_list=my_list, products=product).delete()  # pylint: disable=no-member

        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('home'))


class MyListDeleteItem(LoginRequiredMixin, View):
    def post(self, request, pid):
        WishListItems.objects.filter(pk=pid, wish_list__user=request.user).delete()   # pylint: disable=no-member
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))


 
                
                
                
            
    