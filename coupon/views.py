from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Coupons
from .forms import CouponForm
from decimal import Decimal
from orders.models import Cart
from django.core.paginator import Paginator
from django.utils import timezone


def user_coupon_list(request):
    '''user side coupon listing function'''
    coupon=Coupons.objects.all().order_by('-id')
    page = 1
    if request.GET:
        page = request.GET.get('page', 1)

    user_paginator = Paginator(coupon, 2)
    coupon = user_paginator.get_page(page)
    
    return render(request, 'coupons/user_coupon_view.html', {'coupon': coupon})

def coupon_list(request):
    '''admin side coupon listing function '''
    coupons = Coupons.objects.all().order_by('-id')
    page = 1
    if request.GET:
        page = request.GET.get('page', 1)

    user_paginator = Paginator(coupons, 5)
    coupons = user_paginator.get_page(page)
    
    return render(request, 'coupons/admin_coupon.html', {'coupons': coupons})

def create_coupon(request):
    '''admin side coupon creating function '''
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created successfully!")
            return redirect('coupon_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm()
    return render(request, 'coupons/add_coupon.html', {'form': form})

def delete_coupon(request, coupon_id):
    '''this fuction is not using so leave it '''
    coupon = get_object_or_404(Coupons, id=coupon_id)
    coupon.delete()
    return redirect('coupons:coupon_list')


def update_coupon(request, coupon_id):
    '''this function is for editing the  coupon in admin side'''
    coupon = get_object_or_404(Coupons, id=coupon_id)
    
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f"Coupon '{coupon.coupon_code}' updated successfully!")
            return redirect('coupon_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CouponForm(instance=coupon)
    
    return render(request, 'coupons/update_coupon.html', {
        'form': form,
        'coupon': coupon,
        'is_update': True
    })
    
    
    
def apply_coupon(request):
    if request.method == "POST":
        print("**********************************************************************")
        print("the coupon aplying starts here ")
        print("**********************************************************************")
        
        code = request.POST.get("coupon_code", "").strip()
        print(f"coupon code is {code}")

        if not code:
            messages.error(request, "Please enter a coupon code.",extra_tags='coupon-tag')
            print("no code found")
            return redirect("checkout")

        try:
            user_cart = Cart.objects.get(owner=request.user)
            print(f"The cart belongs to : {user_cart}")
        except Cart.DoesNotExist:
            messages.error(request, "No cart found.")
            print("no cart found")
            return redirect("checkout")

        if not user_cart.ordered_items.exists():
            print("cart is empty")
            messages.error(request, "Your cart is empty.",extra_tags='coupon-tag')
            return redirect("checkout")

        if user_cart.coupon_code and user_cart.coupon_code.coupon_code.lower() == code.lower():
            print("thiis coupon is used just before")
            messages.info(request, "This coupon is already applied.",extra_tags='coupon-tag')
            return redirect("checkout")

        if user_cart.coupon_code:
            old_coupon = user_cart.coupon_code.coupon_code
            user_cart.coupon_code = None
            user_cart.save(update_fields=['coupon_code'])
            print(f"Cleared old coupon: {old_coupon}")

        try:
            coupon = Coupons.objects.get(coupon_code__iexact=code)
        except Coupons.DoesNotExist:
            messages.error(request, "Invalid coupon code.",extra_tags='coupon-tag')
            print("coupon doesn't exist")
            return redirect("checkout")

        if not coupon.is_valid():
            messages.error(request, "This coupon is expired, inactive, or used up.",extra_tags='coupon-tag')
            print("coupon is expired ")
            return redirect("checkout")

        if user_cart.subtotal < coupon.min_cart_value:
            messages.error(request, f"Cart must be at least ₹{coupon.min_cart_value} to use this coupon.",extra_tags='coupon-tag')
            print(f"Cart must be at least ₹{coupon.min_cart_value} to use this coupon.")
            return redirect("checkout")

        user_cart.coupon_code = coupon
        user_cart.save(update_fields=['coupon_code'])

        messages.success(request, f"Coupon '{coupon.coupon_code}' applied! You saved ₹{coupon.discount_value}.")
        print("coupon applyed successfully")
        return redirect("checkout")
    print("geting get request ")
    return redirect("checkout")


# def remove_coupon(request):
#     """Remove applied coupon from cart"""
#     try:
#         user_cart = Cart.objects.get(owner=request.user)
#         print("🗑️ remove_coupon called")
#         if user_cart.coupon:  # ✅ FIXED: use 'coupon' not 'coupon_code'
#             coupon_name = user_cart.coupon.coupon_code
#             user_cart.coupon = None
#             user_cart.save(update_fields=['coupon'])
#             messages.success(request, f"Coupon '{coupon_name}' removed successfully.")
#             print(f"✅ Coupon '{coupon_name}' removed")
#         else:
#             print("❌ No coupon to remove")
#     except Cart.DoesNotExist as e:
#         print(f"❌ Cart not found: {str(e)}")
#         messages.error(request, "No cart found.")
    
#     return redirect("checkout")
def remove_coupon(request):
    """Remove applied coupon from cart"""
    try:
        user_cart = Cart.objects.get(owner=request.user)
        print(" remove_coupon working in line 115 (coupon.views.remove_coupon)")
        if user_cart.coupon_code:
            user_cart.coupon_code = None
            user_cart.save(update_fields=['coupon_code'])
            messages.success(request, "Coupon removed successfully.")
    except Cart.DoesNotExist as e:
        print(f"error of exiting is {str(e)}")
        messages.error(request, "No cart found.")
    
    return redirect("checkout")
