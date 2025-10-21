from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Referral, ReferralReward, Register, ReferralCode
from wallet.models import Wallet, WalletTransaction
from offer.models import Offers


# @receiver(post_save, sender=Register)
# def create_referral_code_for_user(sender, instance, created, **kwargs):
#     """Automatically create referral code when user registers"""
#     if created:
#         ReferralCode.objects.get_or_create(
#             user=instance,
#             defaults={'code': ReferralCode.generate_unique_code(instance)}
#         )
#         print(f"✅ Referral code created for {instance.email}")


@receiver(post_save, sender=Referral)
def process_referral_rewards_on_first_purchase(sender, instance, created, **kwargs):
    """
    Automatically credit wallets when referred user makes first purchase
    This triggers when Referral.first_purchase_at is set
    """
    # Only process if:
    # 1. first_purchase_at is set (user made their first purchase)
    # 2. status is still PENDING (rewards not yet given)
    if instance.first_purchase_at and instance.status == Referral.PENDING:
        print(f"🎉 Processing referral rewards for {instance}")
        
        try:
            # Get active referral offer
            active_offer = Offers.objects.filter(
                offer_type='referral',
                active=True,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).first()
            
            if not active_offer:
                print("⚠️ No active referral offer found - skipping wallet credit")
                # Still mark as processed to avoid reprocessing
                instance.status = Referral.BOTH_REWARDED
                instance.save(update_fields=['status'])
                return
            
            # Calculate reward amounts
            # Option 1: Use fixed amount
            referrer_amount = Decimal('100.00')
            referee_amount = Decimal('50.00')
            
            # Option 2: Use offer's discount_percent as amount
            # referrer_amount = Decimal(str(active_offer.discount_percent))
            # referee_amount = Decimal(str(active_offer.discount_percent / 2))
            
            print(f"💰 Reward amounts - Referrer: ₹{referrer_amount}, Referee: ₹{referee_amount}")
            
            # ========================================
            # CREDIT REFERRER's WALLET
            # ========================================
            referrer_wallet, _ = Wallet.objects.get_or_create(user=instance.referrer)
            referrer_transaction = referrer_wallet.add_money(
                amount=referrer_amount,
                transaction_type=WalletTransaction.CREDIT_REFERRAL,
                description=f"Referral bonus for inviting {instance.referred.email}",
                reference_id=f"REF-{instance.id}"
            )
            print(f"✅ Credited ₹{referrer_amount} to {instance.referrer.email}'s wallet")
            
            # Create referrer reward record
            referrer_reward = ReferralReward.objects.create(
                referral=instance,
                user=instance.referrer,
                reward_type=ReferralReward.REFERRER_BONUS,
                offer=active_offer,
                discount_amount=referrer_amount,
                is_used=True,  # Wallet credit is immediately "used"
                used_at=timezone.now(),
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(days=365)
            )
            print(f"✅ Referrer reward record created: {referrer_reward}")
            
            # ========================================
            # CREDIT REFEREE's WALLET (Welcome Bonus)
            # ========================================
            referee_wallet, _ = Wallet.objects.get_or_create(user=instance.referred)
            referee_transaction = referee_wallet.add_money(
                amount=referee_amount,
                transaction_type=WalletTransaction.CREDIT_REFERRAL,
                description=f"Welcome bonus! Referred by {instance.referrer.email}",
                reference_id=f"REF-{instance.id}"
            )
            print(f" Credited ₹{referee_amount} to {instance.referred.email}'s wallet")
            
            # Create referee reward record
            referee_reward = ReferralReward.objects.create(
                referral=instance,
                user=instance.referred,
                reward_type=ReferralReward.REFEREE_BONUS,
                offer=active_offer,
                discount_amount=referee_amount,
                is_used=True,  
                used_at=timezone.now(),
                valid_from=timezone.now(),
                valid_until=timezone.now() + timedelta(days=365)
            )
            print(f" Referee reward record created: {referee_reward}")
            

            instance.status = Referral.BOTH_REWARDED
            instance.save(update_fields=['status'])
            print(f"✅ Referral status updated to BOTH_REWARDED")
            
            print(f"🎊 SUCCESS! Referral rewards processed completely for referral ID {instance.id}")
            
        except Exception as e:
            print(f"❌ ERROR processing referral rewards: {str(e)}")
            import traceback
            traceback.print_exc()
            # 


@receiver(post_save, sender=ReferralCode)
def log_referral_code_creation(sender, instance, created, **kwargs):
    """Log when referral codes are created"""
    if created:
        print(f"📝 New referral code created: {instance.code} for {instance.user.email}")