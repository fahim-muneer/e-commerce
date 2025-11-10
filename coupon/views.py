from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Coupons, CouponUsage
from .forms import CouponForm
from decimal import Decimal
from orders.models import Cart
from django.core.paginator import Paginator
from django.utils import timezone
from loguru import logger
import os

LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coupon_logs.log')

logger.add(LOG_FILE_PATH, rotation="10 MB", retention="10 days", level="INFO")


def user_coupon_list(request):
    """Show available coupons to users with their usage info"""
    coupons = Coupons.objects.filter(
        active=True,
        expire_at__gte=timezone.now().date()
    ).order_by('-id')

    coupon_list_data = []

    for coupon in coupons:
        if request.user.is_authenticated:
            used_count = coupon.get_usage_count(request.user)
            remaining = coupon.use_limit_per_user - used_count
        else:
            used_count = 0
            remaining = coupon.use_limit_per_user

        can_use = remaining > 0

        coupon_list_data.append({
            'coupon': coupon,
            'used_count': used_count,
            'remaining_uses': remaining,
            'can_use': can_use
        })

    page = request.GET.get('page', 1)
    paginator = Paginator(coupon_list_data, 2)
    coupon_page_obj = paginator.get_page(page)

    context = {
        'coupon': coupon_page_obj  
    }
    return render(request, 'coupons/user_coupon_view.html', context)



def coupon_list(request):
    """Admin view for all coupons"""
    coupons = Coupons.objects.all().order_by('-id')
    coupon_stats = []
    for coupon in coupons:
        total_uses = CouponUsage.objects.filter(coupon=coupon).count()
        unique_users = CouponUsage.objects.filter(
            coupon=coupon
        ).values('user').distinct().count()
        
        coupon_stats.append({
            'coupon': coupon,
            'total_uses': total_uses,
            'unique_users': unique_users
        })
    
    page = request.GET.get('page', 1)
    user_paginator = Paginator(coupon_stats, 5)
    coupons_page = user_paginator.get_page(page)
    
    return render(request, 'coupons/admin_coupon.html', {'coupons': coupons_page})


def create_coupon(request):
    if request.method == 'POST':
        
        form = CouponForm(request.POST)
        if form.is_valid():
            
            form.save()
            
            messages.success(request, "Coupon created successfully!")
            
            return redirect('coupon_list')
        else:
            
            logger.error("the form is not validated yet ")

    else:
        
        form = CouponForm()
        
    return render(request, 'coupons/admin_coupon.html', {'form': form})


def update_coupon(request, coupon_id):
    coupon = get_object_or_404(Coupons, id=coupon_id)
    
    if request.method == 'POST':
        
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            
            form.save()
            
            messages.success(
                request, 
                f"Coupon '{coupon.coupon_code}' updated successfully!"
            )
            
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
    """Apply coupon with user-specific validation"""
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()

        if not code:
            messages.error(
                request, 
                "Please enter a coupon code.", 
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        if not request.user.is_authenticated:
            messages.error(
                request, 
                "Please login to use coupons.", 
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        try:
            user_cart = Cart.objects.get(owner=request.user)
        except Cart.DoesNotExist:
            messages.error(request, "No cart found.", extra_tags='coupon-tag')
            return redirect("checkout")

        if not user_cart.ordered_items.exists():
            messages.error(
                request, 
                "Your cart is empty.", 
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        if (user_cart.coupon_code and 
            user_cart.coupon_code.coupon_code.lower() == code.lower()):
            messages.info(
                request, 
                "This coupon is already applied.", 
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        if user_cart.coupon_code:
            user_cart.coupon_code = None
            user_cart.save(update_fields=['coupon_code'])

        try:
            coupon = Coupons.objects.get(coupon_code__iexact=code)
        except Coupons.DoesNotExist:
            messages.error(
                request, 
                "Invalid coupon code.", 
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        is_valid, error_message = coupon.is_valid(user=request.user)
        if not is_valid:
            messages.error(request, error_message, extra_tags='coupon-tag')
            return redirect("checkout")

        if user_cart.subtotal < coupon.min_cart_value:
            messages.error(
                request, 
                f"Cart must be at least ₹{coupon.min_cart_value} to use this coupon.",
                extra_tags='coupon-tag'
            )
            return redirect("checkout")

        user_cart.coupon_code = coupon
        user_cart.save(update_fields=['coupon_code'])

        remaining = coupon.get_remaining_uses(request.user)
        
        messages.success(
            request, 
            f"Coupon '{coupon.coupon_code}' applied! You saved ₹{coupon.discount_value}. "
            f"You have {remaining} use(s) remaining for this coupon.",
            extra_tags='coupon-tag'
        )
        return redirect("checkout")
    
    return redirect("checkout")


def remove_coupon(request):
    """Remove applied coupon from cart"""
    try:
        user_cart = Cart.objects.get(owner=request.user)
        if user_cart.coupon_code:
            user_cart.coupon_code = None
            user_cart.save(update_fields=['coupon_code'])
            messages.success(
                request, 
                "Coupon removed successfully.", 
                extra_tags='coupon-tag'
            )
        else:
            messages.info(
                request, 
                "No coupon was applied to your cart.", 
                extra_tags='coupon-tag'
            )
    except Cart.DoesNotExist:
        messages.error(
            request, 
            "No cart found.", 
            extra_tags='coupon-tag'
        )
    
    return redirect("checkout")
