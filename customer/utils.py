from django.utils import timezone
from .models import Referral, ReferralCode, Register


def mark_referral_first_purchase(user):
    """
    Mark that a referred user has made their first purchase
    This will trigger the signal to credit wallets automatically
    
    ⚠️ IMPORTANT: Call this in your order success/payment success view!
    
    Usage:
        from customer.utils import mark_referral_first_purchase
        
        # In your order completion view (after payment success):
        mark_referral_first_purchase(request.user)
    
    Args:
        user: The user who just completed their first purchase (Register instance)
    
    Returns:
        dict: Status information about the referral marking
    """
    try:
        # Find if this user was referred by someone
        referral = Referral.objects.filter(
            referred=user,
            first_purchase_at__isnull=True  # Only if not already marked
        ).first()
        
        if referral:
            # Mark the first purchase time
            referral.first_purchase_at = timezone.now()
            referral.save()  # This triggers the signal to credit wallets!
            
            print(f"✅ First purchase marked for referral: {referral}")
            print(f"   Referrer: {referral.referrer.email}")
            print(f"   Referred: {referral.referred.email}")
            
            return {
                'success': True,
                'message': f'Referral bonus will be credited to {referral.referrer.email}',
                'referral': referral
            }
        else:
            print(f"ℹ️ No pending referral found for user: {user.email}")
            return {
                'success': False,
                'message': 'No pending referral found',
                'referral': None
            }
            
    except Exception as e:
        print(f"❌ Error marking referral first purchase: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e),
            'referral': None
        }


def create_referral_on_signup(referred_user, referral_code_str):
    """
    Create a referral record when user signs up with a referral code
    
    ⚠️ IMPORTANT: Call this in your signup view after creating the user!
    
    Usage:
        from customer.utils import create_referral_on_signup
        
        # In your signup view after user creation:
        ref_code = request.GET.get('ref') or request.POST.get('referral_code')
        if ref_code:
            result = create_referral_on_signup(new_user, ref_code)
            if result['success']:
                messages.success(request, f"You'll get ₹50 bonus after your first purchase!")
    
    Args:
        referred_user: The newly registered user (Register instance)
        referral_code_str: The referral code string (e.g., 'ABC123XYZ')
    
    Returns:
        dict: Status information about referral creation
    """
    try:
        # Find the referral code
        referral_code_obj = ReferralCode.objects.filter(code=referral_code_str).first()
        
        if not referral_code_obj:
            print(f"❌ Invalid referral code: {referral_code_str}")
            return {
                'success': False,
                'message': 'Invalid referral code',
                'referral': None
            }
        
        # Don't allow self-referral
        if referral_code_obj.user == referred_user:
            print(f"❌ Self-referral attempt blocked for {referred_user.email}")
            return {
                'success': False,
                'message': 'You cannot refer yourself',
                'referral': None
            }
        
        # Check if user already has a referral
        existing = Referral.objects.filter(referred=referred_user).first()
        if existing:
            print(f"⚠️ User {referred_user.email} already has a referral: {existing}")
            return {
                'success': False,
                'message': 'User already referred',
                'referral': existing
            }
        
        # Create referral record
        referral = Referral.objects.create(
            referrer=referral_code_obj.user,
            referred=referred_user,
            referral_code=referral_code_obj,
            signed_up_at=timezone.now()
        )
        
        # Store in Register model for reference
        referred_user.referred_by_code = referral_code_str
        referred_user.save(update_fields=['referred_by_code'])
        
        print(f"✅ Referral created successfully!")
        print(f"   Referrer: {referral.referrer.email}")
        print(f"   Referred: {referral.referred.email}")
        print(f"   Code: {referral_code_str}")
        
        return {
            'success': True,
            'message': f'Successfully used referral code from {referral.referrer.full_name}',
            'referral': referral
        }
        
    except Exception as e:
        print(f"❌ Error creating referral: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': str(e),
            'referral': None
        }


def get_user_referral_stats(user):
    """
    Get referral statistics for a user
    
    Usage:
        stats = get_user_referral_stats(request.user)
        print(f"Total earnings: ₹{stats['total_earnings']}")
    """
    from decimal import Decimal
    
    referrals_made = Referral.objects.filter(referrer=user)
    successful = referrals_made.filter(first_purchase_at__isnull=False)
    
    total_earnings = user.total_referral_earnings
    
    return {
        'total_referrals': referrals_made.count(),
        'successful_referrals': successful.count(),
        'pending_referrals': referrals_made.filter(first_purchase_at__isnull=True).count(),
        'total_earnings': total_earnings,
        'referral_code': user.get_referral_code(),
    }


def check_and_apply_referral_on_first_order(order, user):
    """
    Check if this is user's first order and apply referral bonus
    
    ⚠️ Call this in your order creation/payment success handler
    
    Usage:
        from customer.utils import check_and_apply_referral_on_first_order
        
        # After order is successfully placed:
        check_and_apply_referral_on_first_order(order, request.user)
    """
    try:
        from orders.models import Orders  # Adjust import as needed
        
        # Check if this is the first order
        user_orders = Orders.objects.filter(user=user, is_paid=True).count()
        
        if user_orders == 1:  # This is the first paid order
            print(f"🎯 First order detected for {user.email}")
            result = mark_referral_first_purchase(user)
            
            if result['success']:
                print(f"🎉 Referral bonuses will be credited!")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error in check_and_apply_referral_on_first_order: {str(e)}")
        return False