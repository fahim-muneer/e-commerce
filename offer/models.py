from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Offers(models.Model):
    OFFER_TYPE_CHOICES = (
        ('category', 'Category Offer'),
        ('product', 'Product Offer'),
        ('referral', 'Referral Offer'),
    )

    APPLIES_TO_CHOICES = (
        ('referrer', 'Referrer'),
        ('referee', 'Referee'),
        ('both', 'Both'),
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    offer_type = models.CharField(max_length=20, choices=OFFER_TYPE_CHOICES)

    applies_to = models.CharField(
        max_length=20,
        choices=APPLIES_TO_CHOICES,
        default='both',
        help_text="Who this referral offer applies to"
    )

    fixed_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Fixed bonus amount for referral reward"
    )

    percentage_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Optional percentage bonus"
    )

    validity_days = models.PositiveIntegerField(
        default=30,
        help_text="Reward validity duration in days"
    )

    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Enter discount in percentage (e.g., 10 for 10%)"
    )

    categories = models.ManyToManyField(
        'category.CategoryPage',
        blank=True,
        related_name='offers'
    )

    products = models.ManyToManyField(
        'products.ProductPage',
        blank=True,
        related_name='offers'
    )

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(default=timezone.now)

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        now = timezone.now()
        return self.active and self.start_date <= now <= self.end_date

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError('End date must be after start date.')

        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError('Discount must be between 0 and 100.')

    def __str__(self):
        return f"{self.name} ({self.get_offer_type_display()}) - {self.discount_percent}%"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Offer'
        verbose_name_plural = 'Offers'

