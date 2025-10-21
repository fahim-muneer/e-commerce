from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from datetime import timedelta
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField 
import re
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid

def realistic_pin_validator(value):
    if not re.match(r'^[1-9][0-9]{5}$', value):
        raise ValidationError('Enter a valid 6-digit Indian PIN code.')
   
    if len(set(value)) == 1:
        raise ValidationError('Enter a valid Indian PIN code, not repeated digits.')


class MyAccountManager(BaseUserManager):
    def create_user(self, full_name, email, password=None):
        if not email:
            raise ValueError("Email must be set")
        if not full_name:
            raise ValueError("Full name must be set")
        
        user = self.model(
            email=self.normalize_email(email),
            full_name=full_name,
        )
        user.set_password(password)
        user.is_active = True  
        user.save(using=self._db)
        return user
    
    def create_superuser(self, full_name, email, password):
        user = self.create_user(
            full_name=full_name,
            email=email,
            password=password,
        )
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Register(AbstractBaseUser):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(max_length=300, unique=True)
    
    referred_by_code = models.CharField(
        max_length=20, 
        null=True, 
        blank=True, 
        help_text="Referral code used during signup"
    )
    
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True) 
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = MyAccountManager()

    def __str__(self):
        return str(self.email)

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser
    
    def get_referral_code(self):
        """Get or create referral code for this user"""
        code_obj, created = ReferralCode.objects.get_or_create(
            user=self,
            defaults={'code': ReferralCode.generate_unique_code(self)}
        )
        return code_obj.code
    
    def get_available_referral_rewards(self):
        """Get all valid, unused referral rewards"""
        return ReferralReward.objects.filter(
            user=self,
            is_used=False,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        )
    
    @property
    def total_referral_earnings(self):
        """Calculate total earnings from referrals"""
        total = ReferralReward.objects.filter(
            user=self,
            reward_type=ReferralReward.REFERRER_BONUS
        ).aggregate(
            total=models.Sum('discount_amount')
        )['total']
        return total or Decimal('0')
    
    @property
    def successful_referrals_count(self):
        """Count successful referrals (where referee made first purchase)"""
        return Referral.objects.filter(
            referrer=self,
            first_purchase_at__isnull=False
        ).count()


class OTP(models.Model):
    user = models.OneToOneField(Register, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)  
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        expiration_time = self.created_at + timedelta(minutes=5)
        return timezone.now() <= expiration_time

    def __str__(self):
        return f"OTP for {self.user.email}"


class AddressType(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.name)


class UserAddress(models.Model):
    user = models.ForeignKey(Register, on_delete=models.CASCADE, related_name='user_address')
    mobile = PhoneNumberField(blank=False) 
    second_mob = PhoneNumberField(blank=True, null=True) 
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=200)
    pin = models.CharField(max_length=6, validators=[realistic_pin_validator])
    address_type = models.ForeignKey(AddressType, on_delete=models.CASCADE)
    is_default = models.BooleanField(default=False)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Customer(models.Model):
    profile_picture = models.ImageField(upload_to='customer/', null=True)
    user = models.OneToOneField(Register, on_delete=models.CASCADE, related_name='cusomer_profile')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.user.full_name)
    
    
    
    
    
    
    
    
    
class ReferralCode(models.Model):
    """Unique referral code for each user"""
    user = models.OneToOneField(Register, on_delete=models.CASCADE, related_name='referral_code_obj')
    code = models.CharField(max_length=20, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    @classmethod
    def generate_unique_code(cls, user):
        """Generate a unique referral code for a user"""
        # Use email for code generation
        base_code = user.email[:6].upper().replace('@', '').replace('.', '')
        unique_suffix = str(uuid.uuid4())[:6].upper()
        code = f"{base_code}{unique_suffix}"
        
        # Ensure uniqueness
        while cls.objects.filter(code=code).exists():
            unique_suffix = str(uuid.uuid4())[:6].upper()
            code = f"{base_code}{unique_suffix}"
        
        return code


class Referral(models.Model):
    """Track who referred whom"""
    referrer = models.ForeignKey(Register, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.OneToOneField(Register, on_delete=models.CASCADE, related_name='referred_by_rel')
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.SET_NULL, null=True)
    
    # Tracking
    signed_up_at = models.DateTimeField(auto_now_add=True)
    first_purchase_at = models.DateTimeField(null=True, blank=True)
    
    # Rewards status
    PENDING = 0
    REFERRER_REWARDED = 1
    BOTH_REWARDED = 2
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (REFERRER_REWARDED, 'Referrer Rewarded'),
        (BOTH_REWARDED, 'Both Rewarded'),
    )
    status = models.IntegerField(choices=STATUS_CHOICES, default=PENDING)
    
    class Meta:
        verbose_name = 'Referral'
        verbose_name_plural = 'Referrals'
    
    def __str__(self):
        return f"{self.referrer.email} referred {self.referred.email}"


class ReferralReward(models.Model):
    """Track rewards earned from referrals"""
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='rewards')
    user = models.ForeignKey(Register, on_delete=models.CASCADE, related_name='referral_rewards')
    
    REFERRER_BONUS = 'referrer'
    REFEREE_BONUS = 'referee'
    REWARD_TYPE_CHOICES = (
        (REFERRER_BONUS, 'Referrer Bonus'),
        (REFEREE_BONUS, 'Referee Bonus'),
    )
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES)
    
    # Reward details
    offer = models.ForeignKey('offer.Offers', on_delete=models.SET_NULL, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    order = models.ForeignKey('orders.Orders', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_reward_type_display()} - {self.user.email} - ₹{self.discount_amount}"
    
    def is_valid(self):
        """Check if reward is still valid"""
        now = timezone.now()
        return not self.is_used and self.valid_from <= now <= self.valid_until
    
    def mark_as_used(self, order):
        """Mark reward as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.order = order
        self.save()
    