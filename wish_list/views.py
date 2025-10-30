from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from products.models import ProductPage
from .models import WishList, WishListItems
from customer.models import Customer


class MyList(LoginRequiredMixin, View):
    def get(self, request):
        profile = get_object_or_404(Customer, user=request.user)
        my_list, _ = WishList.objects.get_or_create(user=request.user)
        wishlist_items = WishListItems.objects.filter(wish_list=my_list)

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
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if product_id and action:
            try:
                product = get_object_or_404(ProductPage, pk=product_id)
                my_list, _ = WishList.objects.get_or_create(user=request.user)

                if action == 'add':
                    item, created = WishListItems.objects.get_or_create(
                        wish_list=my_list, 
                        products=product
                    )
                    
                    if is_ajax:
                        if created:
                            return JsonResponse({
                                'success': True,
                                'message': f'{product.name} added to wishlist!',
                                'action': 'added'
                            })
                        else:
                            return JsonResponse({
                                'success': True,
                                'message': f'{product.name} is already in your wishlist.',
                                'action': 'already_exists'
                            })
                
                elif action == 'remove':
                    deleted_count, _ = WishListItems.objects.filter(
                        wish_list=my_list, 
                        products=product
                    ).delete()
                    
                    if is_ajax:
                        if deleted_count > 0:
                            return JsonResponse({
                                'success': True,
                                'message': f'{product.name} removed from wishlist!',
                                'action': 'removed'
                            })
                        else:
                            return JsonResponse({
                                'success': False,
                                'message': 'Item not found in wishlist.',
                                'action': 'not_found'
                            })
            
            except ProductPage.DoesNotExist:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'Product not found.'
                    })
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'An error occurred. Please try again.'
                    })
        else:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid request.'
                })

        # For non-AJAX requests, redirect as before
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('home'))


class MyListDeleteItem(LoginRequiredMixin, View):
    def post(self, request, pid):
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            deleted_count, _ = WishListItems.objects.filter(
                pk=pid, 
                wish_list__user=request.user
            ).delete()
            
            if is_ajax:
                if deleted_count > 0:
                    return JsonResponse({
                        'success': True,
                        'message': 'Item removed from wishlist!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Item not found in wishlist.'
                    })
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'An error occurred. Please try again.'
                })
        
        # For non-AJAX requests, redirect as before
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))


# home/views.py - Update the Unlike view

class Unlike(LoginRequiredMixin, View):
    def post(self, request, pid):
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            deleted_count, _ = WishListItems.objects.filter(
                products_id=pid, 
                wish_list__user=request.user
            ).delete()
            
            if is_ajax:
                if deleted_count > 0:
                    return JsonResponse({
                        'success': True,
                        'message': 'Removed from wishlist!'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Item not found in wishlist.'
                    })
        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'An error occurred. Please try again.'
                })
        
        # For non-AJAX requests, redirect as before
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))