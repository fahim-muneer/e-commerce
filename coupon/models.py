from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class Coupons(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    coupon_code = models.CharField(max_length=50, unique=True, blank=False)
    description = models.TextField(blank=True, null=True)
    min_cart_value = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    
    discount_type = models.CharField(
        max_length=20, 
        choices=DISCOUNT_TYPE_CHOICES, 
        default='percentage',
        help_text="Choose between percentage discount or fixed amount"
    )
    discount_value = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        blank=False,
        help_text="For percentage: enter value like 10 for 10%. For fixed: enter amount like 100 for ₹100"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount amount (only for percentage type)"
    )
    
    expire_at = models.DateField(default=timezone.now)
    use_limit_per_user = models.PositiveIntegerField(
        default=1, 
        help_text="How many times each user can use this coupon"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    def calculate_discount(self, cart_subtotal):
        """Calculate the actual discount amount based on type"""
        if self.discount_type == 'percentage':
            discount = (Decimal(str(cart_subtotal)) * Decimal(str(self.discount_value))) / Decimal('100')
            
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            
            return discount
        else:  
            return min(Decimal(str(self.discount_value)), Decimal(str(cart_subtotal)))
    
    def is_valid(self, user=None):
        """Check if coupon is valid for use"""
        if not self.active:
            return False, "Coupon is inactive"
        
        if self.expire_at and self.expire_at < timezone.now().date():
            return False, "Coupon has expired"
        
        if user:
            usage_count = CouponUsage.objects.filter(
                coupon=self,
                user=user
            ).count()
            
            if usage_count >= self.use_limit_per_user:
                return False, f"You have already used this coupon {self.use_limit_per_user} time(s)"
        
        return True, "Valid"

    def get_usage_count(self, user):
        """Get how many times a user has used this coupon"""
        return CouponUsage.objects.filter(coupon=self, user=user).count()
    
    def get_remaining_uses(self, user):
        """Get remaining uses for a user"""
        used = self.get_usage_count(user)
        return max(0, self.use_limit_per_user - used)
    
    def get_discount_display(self):
        """Return human-readable discount format"""
        if self.discount_type == 'percentage':
            display = f"{self.discount_value}% OFF"
            if self.max_discount_amount:
                display += f" (Max ₹{self.max_discount_amount})"
            return display
        else:
            return f"₹{self.discount_value} OFF"

    def __str__(self):
        return f"{self.coupon_code} - {self.get_discount_display()}"
    
    def clean(self):
        if Coupons.objects.exclude(pk=self.pk).filter(coupon_code__iexact=self.coupon_code).exists():
            raise ValidationError("Coupons with this name already exists (case-insensitive).")
        
        if self.discount_type == 'percentage' and (self.discount_value < 0 or self.discount_value > 100):
            raise ValidationError("Percentage discount must be between 0 and 100")


class CouponUsage(models.Model):
    """Track coupon usage by users"""
    coupon = models.ForeignKey(Coupons, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupon_usages')
    used_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey('orders.Orders', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_usage')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Actual discount amount applied")
    
    class Meta:
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['user', '-used_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.coupon_code} on {self.used_at.strftime('%Y-%m-%d')}"