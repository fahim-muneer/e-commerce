from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Coupons(models.Model):
    coupon_code = models.CharField(max_length=50, unique=True,blank=False)
    description = models.TextField(blank=True, null=True)
    min_cart_value = models.DecimalField(max_digits=10, decimal_places=2,blank=False)
    discount_value = models.DecimalField(max_digits=5, decimal_places=2,blank=False)
    expire_at = models.DateField(default=timezone.now)
    use_limit = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    
    def is_valid(self):
        """Check if coupon is valid for use"""
        if not self.active:
            return False
        if self.expire_at and self.expire_at < timezone.now().date():
            return False
        if self.use_limit is not None and self.use_limit <= 0:
            return False
        return True

    def __str__(self):
        return self.coupon_code    
    def clean(self):
        if Coupons.objects.exclude(pk=self.pk).filter(coupon_code__iexact=self.coupon_code).exists():
            raise ValidationError("Coupons with this name already exists (case-insensitive).")
    



