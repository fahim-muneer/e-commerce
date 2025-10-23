
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from customer.models import Referral, ReferralReward, ReferralCode, Register
from offer.models import Offers


def process_referral_signup(referred_user, referral_code):
    """
    Process a new user signup with referral code
    
    Args:
        referred_user: The new user who signed up
        referral_code: The referral code used
    
    Returns:
        Referral object or None
    """
    try:
        # Get the referral code object
        referral_code_obj = ReferralCode.objects.get(code=referral_code)
        referrer = referral_code_obj.user
        
        # Don't allow self-referral
        if referrer == referred_user:
            return None
        
        # Check if this user was already referred
        if Referral.objects.filter(referred=referred_user).exists():
            return None
        
        # Create referral record
        referral = Referral.objects.create(
            referrer=referrer,
            referred=referred_user,
            referral_code=referral_code_obj,
            status=Referral.PENDING
        )
        
        return referral
        
    except ReferralCode.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error processing referral signup: {e}")
        return None


@transaction.atomic
def process_first_purchase(order):
    """
    Process referral rewards when referred user makes first purchase
    
    Args:
        order: The Order object
    
    Returns:
        tuple: (referrer_reward, referee_reward) or (None, None)
    """
    try:
        user = order.user
        
        # Check if this user was referred
        try:
            referral = Referral.objects.get(
                referred=user,
                first_purchase_at__isnull=True
            )
        except Referral.DoesNotExist:
            return None, None
        
        # Update referral record
        referral.first_purchase_at = timezone.now()
        referral.first_order = order
        referral.status = Referral.REFERRED_PURCHASED
        referral.save()
        
        # Get active referral offers
        now = timezone.now()
        referral_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        if not referral_offers.exists():
            return None, None
        
        referrer_reward = None
        referee_reward = None
        
        # Create rewards for both users
        for offer in referral_offers:
            # Reward for referrer
            if offer.applies_to == 'referrer' or offer.applies_to == 'both':
                referrer_reward = create_referral_reward(
                    user=referral.referrer,
                    referral=referral,
                    offer=offer,
                    reward_type='referrer'
                )
                
                # Update referrer's earnings
                update_referrer_earnings(
                    referral.referrer,
                    offer.fixed_discount_amount
                )
            
            # Reward for referee (the new user who made purchase)
            if offer.applies_to == 'referee' or offer.applies_to == 'both':
                referee_reward = create_referral_reward(
                    user=referral.referred,
                    referral=referral,
                    offer=offer,
                    reward_type='referee'
                )
        
        # Update referral status
        if referrer_reward and referee_reward:
            referral.status = Referral.BOTH_REWARDED
        elif referrer_reward:
            referral.status = Referral.REFERRER_REWARDED
        elif referee_reward:
            referral.status = Referral.REFEREE_REWARDED
        
        referral.save()
        
        return referrer_reward, referee_reward
        
    except Exception as e:
        print(f"Error processing first purchase: {e}")
        return None, None


def create_referral_reward(user, referral, offer, reward_type):
    """
    Create a referral reward for a user
    
    Args:
        user: User to receive reward
        referral: Referral object
        offer: Offer object
        reward_type: 'referrer' or 'referee'
    
    Returns:
        ReferralReward object
    """
    try:
        # Calculate validity period
        valid_from = timezone.now()
        validity_days = offer.validity_days or 30
        valid_until = valid_from + timedelta(days=validity_days)
        
        # Create reward
        reward = ReferralReward.objects.create(
            user=user,
            referral=referral,
            offer=offer,
            reward_type=reward_type,
            discount_amount=offer.fixed_discount_amount,
            discount_percentage=offer.percentage_discount or Decimal('0'),
            valid_from=valid_from,
            valid_until=valid_until,
            is_used=False
        )
        
        return reward
        
    except Exception as e:
        print(f"Error creating referral reward: {e}")
        return None


def update_referrer_earnings(referrer, amount):
    """
    Update referrer's total earnings
    
    Args:
        referrer: User who made the referral
        amount: Amount to add to earnings
    """
    try:
        register = Register.objects.get(email=referrer.email)
        
        if register.total_referral_earnings is None:
            register.total_referral_earnings = Decimal('0')
        
        register.total_referral_earnings += amount
        
        if register.successful_referrals_count is None:
            register.successful_referrals_count = 0
        
        register.successful_referrals_count += 1
        register.save()
        
    except Register.DoesNotExist:
        pass
    except Exception as e:
        print(f"Error updating referrer earnings: {e}")


def apply_referral_reward(order, reward):
    """
    Apply a referral reward to an order
    
    Args:
        order: Order object
        reward: ReferralReward object
    
    Returns:
        Decimal: Discount amount applied
    """
    try:
        if reward.is_used:
            return Decimal('0')
        
        if timezone.now() < reward.valid_from or timezone.now() > reward.valid_until:
            return Decimal('0')
        
        # Calculate discount
        discount = Decimal('0')
        
        if reward.discount_amount:
            discount = reward.discount_amount
        elif reward.discount_percentage:
            discount = (order.total_amount * reward.discount_percentage) / Decimal('100')
        
        # Mark reward as used
        reward.is_used = True
        reward.used_at = timezone.now()
        reward.order = order
        reward.save()
        
        return discount
        
    except Exception as e:
        print(f"Error applying referral reward: {e}")
        return Decimal('0')


def get_available_rewards(user):
    """
    Get all available (unused and valid) rewards for a user
    
    Args:
        user: User object
    
    Returns:
        QuerySet of ReferralReward objects
    """
    now = timezone.now()
    return ReferralReward.objects.filter(
        user=user,
        is_used=False,
        valid_from__lte=now,
        valid_until__gte=now
    ).select_related('offer')


def validate_referral_code(code):
    """
    Validate a referral code
    
    Args:
        code: Referral code string
    
    Returns:
        tuple: (is_valid, message, referral_code_obj)
    """
    if not code:
        return False, "Referral code is required", None
    
    try:
        referral_code_obj = ReferralCode.objects.get(code=code.upper())
        
        if not referral_code_obj.is_active:
            return False, "This referral code is no longer active", None
        
        return True, "Valid referral code", referral_code_obj
        
    except ReferralCode.DoesNotExist:
        return False, "Invalid referral code", None