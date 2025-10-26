
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from customer.models import Referral, ReferralReward, Register, ReferralCode
from wallet.models import Wallet, WalletTransaction
from offer.models import Offers
from orders.models import Orders
from allauth.socialaccount.signals import pre_social_login, social_account_added
from django.dispatch import receiver
from allauth.socialaccount.models import SocialAccount
from .models import Customer, ReferralCode

@receiver(pre_social_login)
def populate_user_from_google(sender, request, sociallogin, **kwargs):
    """
    Populate user data from Google account before login
    """
    user = sociallogin.user
    
    if sociallogin.account.provider == 'google':
        data = sociallogin.account.extra_data
        
        # Extract name data from Google
        first_name = data.get('given_name', '')
        last_name = data.get('family_name', '')
        full_name = data.get('name', '')
        
        # Update user fields
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        if full_name:
            user.full_name = full_name
        elif first_name or last_name:
            user.full_name = f"{first_name} {last_name}".strip()
        
        if not user.email and data.get('email'):
            user.email = data.get('email')


@receiver(social_account_added)
def create_user_profile_on_social_signup(sender, request, sociallogin, **kwargs):
    """
    Create Customer profile and Referral code after Google signup
    """
    user = sociallogin.user
    
    # Create Customer profile if it doesn't exist
    Customer.objects.get_or_create(user=user)
    
    # Create Referral Code if it doesn't exist
    ReferralCode.objects.get_or_create(
        user=user,
        defaults={'code': ReferralCode.generate_unique_code(user)})

@receiver(pre_save, sender=Orders)
def track_order_status_change(sender, instance, **kwargs):
    """Track the previous order status before saving"""
    if instance.pk:
        try:
            instance._previous_status = Orders.objects.get(pk=instance.pk).order_status
        except Orders.DoesNotExist:
            instance._previous_status = None
    else:
        instance._previous_status = None


@receiver(post_save, sender=Orders)
def handle_order_referral_rewards(sender, instance, created, **kwargs):
    """
    Automatically process referral rewards when an order is confirmed
    Triggers on status change to CONFIRMED or DELIVERED
    """
    
    if created:
        return
    
    
    previous_status = getattr(instance, '_previous_status', None)
    current_status = instance.order_status
    
    print(f"\n{'='*80}")
    print(f" Order Status Change Detected")
    print(f"   Order ID: {instance.order_Id}")
    print(f"   Previous: {previous_status}")
    print(f"   Current: {current_status}")
    print(f"   User: {instance.user.email}")
    
    
    if (previous_status not in [Orders.STATUS_CONFIRMED, Orders.STATUS_DELIVERED] and 
        current_status in [Orders.STATUS_CONFIRMED, Orders.STATUS_DELIVERED]):
        
        print(f" Status changed to confirmed/delivered")
        
        
        confirmed_orders = Orders.objects.filter(
            user=instance.user,
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_DELIVERED]
        ).order_by('created_at')
        
        print(f" Total confirmed orders for user: {confirmed_orders.count()}")
        
        if confirmed_orders.count() == 1 and confirmed_orders.first() == instance:
            print(f" This is the FIRST confirmed order!")
            
            # Process first purchase
            from customer.views import process_first_purchase
            referral, _ = process_first_purchase(instance.user, instance)
            
            if referral:
                print(f" First purchase processing initiated")
            else:
                print(f" No referral to process")
        else:
            print(f" Not the first order - skipping referral processing")
    else:
        print(f" No relevant status change - skipping")
    
    print(f"{'='*80}\n")


@receiver(post_save, sender=Referral)
def process_referral_wallet_credits(sender, instance, created, **kwargs):

    if created:
        return
    
    if not instance.first_purchase_at or instance.status != Referral.PENDING:
        return
    
    print(f"\n{'='*80}")
    print(f" PROCESSING WALLET CREDITS FOR REFERRAL")
    print(f"   Referral ID: {instance.id}")
    print(f"   Referrer: {instance.referrer.email}")
    print(f"   Referred: {instance.referred.email}")
    print(f"   First Purchase: {instance.first_purchase_at}")
    
    try:
        now = timezone.now()
        active_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        print(f" Found {active_offers.count()} active offers")
        
        if not active_offers.exists():
            print(" No active referral offers - marking as processed without rewards")
            instance.status = Referral.BOTH_REWARDED
            instance.save(update_fields=['status'])
            print(f"{'='*80}\n")
            return
        
        referrer_rewards_created = 0
        referee_rewards_created = 0
        
        for offer in active_offers:
            print(f"\n Processing Offer: {offer.name}")
            print(f"   Applies to: {offer.applies_to}")
            print(f"   Fixed amount: ₹{offer.fixed_discount_amount}")
            
            validity_days = getattr(offer, 'validity_days', 30) or 30
            valid_until = timezone.now() + timedelta(days=validity_days)
            
            if offer.applies_to in ['referrer', 'both', 'Referrer', 'Both']:
                referrer_amount = offer.fixed_discount_amount or Decimal('100.00')
                
                print(f"\n  Crediting Referrer: ₹{referrer_amount}")
                
                referrer_wallet, _ = Wallet.objects.get_or_create(user=instance.referrer)
                
                referrer_transaction = referrer_wallet.add_money(
                    amount=referrer_amount,
                    transaction_type=WalletTransaction.CREDIT_REFERRAL,
                    description=f"Referral bonus for inviting {instance.referred.email}",
                    reference_id=f"REF-{instance.id}"
                )
                
                print(f"    Wallet credited: Transaction ID {referrer_transaction.transaction_id}")
                
                referrer_reward = ReferralReward.objects.create(
                    referral=instance,
                    user=instance.referrer,
                    reward_type=ReferralReward.REFERRER_BONUS,
                    offer=offer,
                    discount_amount=referrer_amount,
                    is_used=True, 
                    used_at=timezone.now(),
                    valid_from=timezone.now(),
                    valid_until=valid_until
                )
                
                print(f"  Reward record created: ID {referrer_reward.id}")
                
                try:
                    referrer = instance.referrer
                    if referrer.total_referral_earnings is None:
                        referrer.total_referral_earnings = Decimal('0')
                    if referrer.successful_referrals_count is None:
                        referrer.successful_referrals_count = 0
                    
                    referrer.total_referral_earnings += referrer_amount
                    referrer.successful_referrals_count += 1
                    referrer.save(update_fields=['total_referral_earnings', 'successful_referrals_count'])
                    
                    print(f"   Referrer stats updated")
                    print(f"      Total earnings: ₹{referrer.total_referral_earnings}")
                    print(f"      Successful referrals: {referrer.successful_referrals_count}")
                except Exception as e:
                    print(f"    Error updating referrer stats: {e}")
                
                referrer_rewards_created += 1
            
            if offer.applies_to in ['referee', 'both', 'Referee', 'Both']:
                referee_amount = offer.fixed_discount_amount or Decimal('50.00')
                
                print(f"\n    Crediting Referee: ₹{referee_amount}")
                
                referee_wallet, _ = Wallet.objects.get_or_create(user=instance.referred)
                
                referee_transaction = referee_wallet.add_money(
                    amount=referee_amount,
                    transaction_type=WalletTransaction.CREDIT_REFERRAL,
                    description=f"Welcome bonus! Referred by {instance.referrer.email}",
                    reference_id=f"REF-{instance.id}"
                )
                
                print(f"    Wallet credited: Transaction ID {referee_transaction.transaction_id}")
                
                referee_reward = ReferralReward.objects.create(
                    referral=instance,
                    user=instance.referred,
                    reward_type=ReferralReward.REFEREE_BONUS,
                    offer=offer,
                    discount_amount=referee_amount,
                    discount_percentage=offer.percentage_discount or 0,
                    is_used=True,
                    used_at=timezone.now(),
                    valid_from=timezone.now(),
                    valid_until=valid_until
                )
                
                print(f"   Reward record created: ID {referee_reward.id}")
                referee_rewards_created += 1
        
        instance.status = Referral.BOTH_REWARDED
        instance.save(update_fields=['status'])
        
        print(f"\n SUCCESS! Referral processing complete")
        print(f"   Referrer rewards: {referrer_rewards_created}")
        print(f"   Referee rewards: {referee_rewards_created}")
        print(f"   Status: {instance.get_status_display()}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f" ERROR processing referral wallet credits: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*80}\n")


@receiver(post_save, sender=ReferralCode)
def log_referral_code_creation(sender, instance, created, **kwargs):
    if created:
        print(f"New referral code created: {instance.code} for {instance.user.email}")