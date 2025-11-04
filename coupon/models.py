from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class Coupons(models.Model):
    coupon_code = models.CharField(max_length=50, unique=True, blank=False)
    description = models.TextField(blank=True, null=True)
    min_cart_value = models.DecimalField(max_digits=10, decimal_places=2, blank=False)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2, blank=False)
    expire_at = models.DateField(default=timezone.now)
    use_limit_per_user = models.PositiveIntegerField(default=1, help_text="How many times each user can use this coupon")
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    def is_valid(self, user=None):
        """Check if coupon is valid for use"""
        if not self.active:
            return False, "Coupon is inactive"
        
        if self.expire_at and self.expire_at < timezone.now().date():
            return False, "Coupon has expired"
        
        # Check user-specific usage limit
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

    def __str__(self):
        return self.coupon_code
    
    def clean(self):
        if Coupons.objects.exclude(pk=self.pk).filter(coupon_code__iexact=self.coupon_code).exists():
            raise ValidationError("Coupons with this name already exists (case-insensitive).")


class CouponUsage(models.Model):
    """Track coupon usage by users"""
    coupon = models.ForeignKey(Coupons, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupon_usages')
    used_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey('orders.Orders', on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_usage')
    
    class Meta:
        ordering = ['-used_at']
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['user', '-used_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.coupon_code} on {self.used_at.strftime('%Y-%m-%d')}"