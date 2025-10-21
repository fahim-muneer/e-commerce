import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.db.models import F

from customer.models import Register
from category.models import CategoryPage
from datetime import timedelta
from products.models import ProductPage
from django.utils import timezone
from django.contrib.auth import get_user_model
User = get_user_model()
from phonenumber_field.modelfields import PhoneNumberField 
import re
from django.core.exceptions import ValidationError
from products.models import ProductVariants
from decimal import Decimal
from django.db.models import Sum
from coupon.models import Coupons
import logging

logger = logging.getLogger(__name__)


def realistic_pin_validator(value):
    if not re.match(r'^[1-9][0-9]{5}$', value):
        raise ValidationError('Enter a valid 6-digit Indian PIN code.')
   
    if len(set(value)) == 1:
        raise ValidationError('Enter a valid Indian PIN code, not repeated digits.')


class OrderAddress(models.Model):
    user       = models.ForeignKey(Register, on_delete=models.CASCADE, null=True, blank=True)
    mobile     = PhoneNumberField(blank=False) 
    second_mob = PhoneNumberField(blank=True, null=True) 
    address    = models.CharField(max_length=500, blank=False)
    city       = models.CharField(max_length=300, blank=False)
    state      = models.CharField(max_length=200, blank=False)
    pin        = models.CharField(max_length=6, validators=[realistic_pin_validator])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.address}, {self.city}, {self.state} - {self.user.user.username if self.user else 'Unknown'}"


class Cart(models.Model):
    owner = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, related_name='cart')

    CART_STAGE = 0
    ORDER_CONFIRMED = 1
    ORDER_PROCESSED = 2
    ORDER_DELIVERED = 3
    ORDER_REJECTED = 4
    STATUS_CHOICE = (
        (CART_STAGE, 'CART_STAGE'),  
        (ORDER_PROCESSED, 'ORDER_PROCESSED'),
        (ORDER_CONFIRMED, 'ORDER_CONFIRMED'),
        (ORDER_DELIVERED, 'ORDER_DELIVERED'),
        (ORDER_REJECTED, 'ORDER_REJECTED')
    )
    coupon_code = models.ForeignKey(Coupons, on_delete=models.SET_NULL, null=True, blank=True)
    order_status = models.IntegerField(choices=STATUS_CHOICE, default=CART_STAGE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.owner.email if self.owner else 'Anonymous'}"


    @property
    def subtotal(self):
        """Calculate subtotal BEFORE coupon discount (includes product-level discounts)"""
        total = Decimal('0')
        for item in self.ordered_items.all():
            if item.product:
                total += item.item_total
        return total

    @property
    def coupon_discount(self):
        """Get the coupon discount amount"""
        if self.coupon_code and self.coupon_code.is_valid():
            discount = self.coupon_code.discount_value
            return min(discount, self.subtotal)
        return Decimal('0')

    @property
    def total_price(self):
        """Calculate FINAL total price after coupon discount"""
        final_total = self.subtotal - self.coupon_discount
        return max(final_total, Decimal('0'))

    @property
    def total_items(self):
        return sum(item.quantity for item in self.ordered_items.all())

    @property
    def total_savings(self):
        """Total savings from product offers + coupon"""
        product_savings = Decimal('0')
        for item in self.ordered_items.all():
            if item.product and hasattr(item, 'savings'):
                product_savings += item.savings
        return product_savings + self.coupon_discount

class CartItems(models.Model):
    product    = models.ForeignKey(ProductPage, on_delete=models.SET_NULL, null=True, related_name="cart_item")
    variant    = models.ForeignKey(ProductVariants, on_delete=models.SET_NULL, null=True, blank=True)  
    quantity   = models.IntegerField(default=1)
    owner      = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='ordered_items')
    created_at = models.DateTimeField(auto_now_add=True)
            
    class Meta:
        unique_together = ('product', 'owner', 'variant')  
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"
    
    @property
    def unit_price(self):
        if self.variant:
            return self.variant.get_discounted_price()
        return self.product.get_display_price()
    
    @property
    def original_unit_price(self):
        if self.variant:
            return self.variant.get_original_price()
        return self.product.get_original_price()
    
    @property
    def item_total(self):
        price = self.unit_price
        return price * self.quantity if price else Decimal('0')
    
    @property
    def original_item_total(self):
        price = self.original_unit_price
        return price * self.quantity if price else Decimal('0')
    
    @property
    def has_discount(self):
        if not self.product:
            return False
        return self.product.has_active_offer()
    
    @property
    def discount_percentage(self):
        if not self.product:
            return 0
        return self.product.get_discount_percentage()
    
    @property
    def savings(self):
        return self.original_item_total - self.item_total


class Orders(models.Model):
    user             = models.ForeignKey(Register, on_delete=models.SET_NULL, null=True)
    delivery_address = models.ForeignKey(OrderAddress, on_delete=models.SET_NULL, null=True)

    CASH_ON_DELIVERY = 0
    ONLINE_PAYMENT   = 1
    WALLET_PAYMENT   = 2
    PAYMENT_CHOICES = (
        (CASH_ON_DELIVERY, "Cash on Delivery"),
        (ONLINE_PAYMENT, "Online Payment"),
        (WALLET_PAYMENT, "Wallet Payment"),
    )
    payment_method = models.IntegerField(choices=PAYMENT_CHOICES, default=CASH_ON_DELIVERY)

    PAYMENT_PENDING = 0
    PAYMENT_PAID    = 1
    PAYMENT_FAILED  = 2
    PAYMENT_REFUNDED = 3
    PAYMENT_STATUS_CHOICES = (
        (PAYMENT_PENDING, "Payment Pending"),
        (PAYMENT_PAID, "Payment Paid"),
        (PAYMENT_FAILED, "Payment Failed"),
        (PAYMENT_REFUNDED, "Payment Refunded"),
    )
    payment_status = models.IntegerField(choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)

    STATUS_PENDING = 0          # Default status before confirmation
    STATUS_CONFIRMED = 1        # Used after successful payment/COD verification
    STATUS_PROCESSED = 2
    STATUS_DELIVERED = 3
    STATUS_REJECTED = 4
    STATUS_RETURN_REQUESTED = 5
    STATUS_RETURN_APPROVED = 6
    STATUS_RETURNED = 7
    
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_RETURN_REQUESTED, "Return Requested"),
        (STATUS_RETURN_APPROVED, "Return Approved"),
        (STATUS_RETURNED, "Returned"),
    )
    order_status = models.IntegerField(choices=STATUS_CHOICES, default=STATUS_PENDING)
    
    razorpay_order_id = models.CharField(max_length=100, null=True, blank=True, help_text="Razorpay Order ID")
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True, help_text="Razorpay Payment ID")
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True, help_text="Razorpay Signature for verification")
    
    # paypal_order_id = models.CharField(max_length=100, null=True, blank=True, help_text="PayPal Order ID for tracking")
    # paypal_payer_id = models.CharField(max_length=100, null=True, blank=True, help_text="PayPal Payer ID")
    # paypal_capture_id = models.CharField(max_length=100, null=True, blank=True, help_text="PayPal Capture ID")
    
    return_reason = models.TextField(max_length=500, null=True, blank=True)
    order_Id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    product_return_reason = models.TextField(max_length=500, null=True, blank=True)
    
    return_requested_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)  # Set in code via mark_as_paid()
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.ForeignKey(Coupons, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['order_status']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['razorpay_order_id']),
        ]
    
    def mark_as_paid(self, payment_id=None, timestamp=None):
        
        self.payment_status = self.PAYMENT_PAID
        self.paid_at = timestamp or timezone.now()
        if payment_id:
            self.razorpay_payment_id = payment_id
        self.save(update_fields=['payment_status', 'paid_at', 'razorpay_payment_id', 'updated_at'])
        logger.info(f"Order {self.pk} marked as paid")
    
    def mark_as_failed(self, reason=""):
        """
        Mark payment as failed.
        """
        self.payment_status = self.PAYMENT_FAILED
        self.save(update_fields=['payment_status', 'updated_at'])
        logger.warning(f"Order {self.pk} payment failed: {reason}")
    
    def mark_as_refunded(self, reason=""):
        """
        Mark order as refunded (for returns/cancellations).
        """
        self.payment_status = self.PAYMENT_REFUNDED
        self.save(update_fields=['payment_status', 'updated_at'])
        logger.info(f"Order {self.pk} refunded: {reason}")
    
    def should_mark_paid_on_cod(self):
        """
        For COD orders, payment is marked as pending until verified by admin/delivery.
        This can be called to auto-mark as paid after delivery confirmation.
        """
        if self.payment_method == self.CASH_ON_DELIVERY:
            return self.order_status >= self.STATUS_DELIVERED
        return False
    
    def recalculate_total(self):
        """
        Recalculate order total based on active (non-cancelled, non-returned) items
        Call this after cancelling or returning items
        """
        from django.db.models import Sum, Q
        
        # Calculate total from items that are NOT cancelled (4) or returned (7)
        total = self.items.exclude(
            order_status__in=[self.STATUS_REJECTED, self.STATUS_RETURNED]
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        
        self.total_amount = total
        self.save(update_fields=['total_amount'])
        return total
    
    def get_active_items_total(self):
        """Get total of only active items (not cancelled/returned)"""
        from django.db.models import Sum
        
        total = self.items.exclude(
            order_status__in=[self.STATUS_REJECTED, self.STATUS_RETURNED]
        ).aggregate(
            total=Sum(F('quantity') * F('unit_price'))
        )['total'] or Decimal('0')
        
        return total
    
    @property
    def can_return(self):
        """Check if *any* ACTIVE delivered item is still eligible for return."""
        delivered_items = self.items.filter(order_status=self.STATUS_DELIVERED)
        if not delivered_items.exists():
            return False
        return any(item.can_return for item in delivered_items)
    
    @property
    def days_left_for_return(self):
        """Get the maximum remaining days for return among delivered items."""
        max_days = 0
        for item in self.items.filter(order_status=self.STATUS_DELIVERED):
            if item.can_return:
                max_days = max(max_days, item.days_left_for_return)
        return max_days
    
    def update_order_status(self):
        """Update order status based on all item statuses"""
        statuses = self.items.values_list('order_status', flat=True)
        
        if not statuses:
            return
        
        if all(s == self.STATUS_DELIVERED for s in statuses):
            self.order_status = self.STATUS_DELIVERED
        elif any(s == self.STATUS_RETURN_REQUESTED for s in statuses):
            self.order_status = self.STATUS_RETURN_REQUESTED
        elif any(s == self.STATUS_RETURN_APPROVED for s in statuses):
            self.order_status = self.STATUS_RETURN_APPROVED
        elif all(s == self.STATUS_RETURNED for s in statuses):
            self.order_status = self.STATUS_RETURNED
        elif all(s == self.STATUS_REJECTED for s in statuses):
            self.order_status = self.STATUS_REJECTED
        elif any(s == self.STATUS_PROCESSED for s in statuses):
            self.order_status = self.STATUS_PROCESSED
        elif all(s == self.STATUS_CONFIRMED for s in statuses):
            self.order_status = self.STATUS_CONFIRMED
        else:
            self.order_status = self.STATUS_PENDING
        
        self.save(update_fields=['order_status'])

    def __str__(self):
        return f"Order #{self.id} - {self.user} - {self.get_payment_status_display()}"

    @property
    def is_payment_complete(self):
        """Check if payment is complete"""
        return self.payment_status == self.PAYMENT_PAID
    
    @property
    def is_paid_or_cod_pending(self):
        """Check if order can proceed (paid online or COD pending)"""
        if self.payment_method == self.ONLINE_PAYMENT:
            return self.payment_status == self.PAYMENT_PAID
        # For COD/Wallet, assume it can proceed
        return True
    def get_item_discount_share(self, item):
        """
        Returns the proportional discount share for a given item
        based on the order's total and discount value.
        """
        if not self.coupon_code or not self.total_amount:
            return Decimal('0.00')

        # Total before discount
        total_before_discount = sum(
            i.total_price for i in self.items.all()
        )

        # Avoid division by zero
        if total_before_discount == 0:
            return Decimal('0.00')

        # Proportion of item in total
        item_ratio = item.total_price / total_before_discount
        total_discount = getattr(self, "discount_value", Decimal('0.00'))

        return (item_ratio * total_discount).quantize(Decimal('0.01'))


class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductPage, on_delete=models.CASCADE, related_name='order_items')
    variant = models.ForeignKey(ProductVariants, on_delete=models.SET_NULL, null=True, blank=True) 
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) 
    
    STATUS_CHOICES = (
        (0, "Pending"),
        (1, "Confirmed"),
        (2, "Processed"),
        (3, "Delivered"),
        (4, "Cancelled"),
        (5, "Return Requested"),
        (6, "Return Approved"),
        (7, "Returned"),
    )
    order_status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    return_reason = models.TextField(max_length=500, blank=True, null=True)
    item_cancel_reason = models.TextField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    RETURN_WINDOW_DAYS = 2
    
    @property
    def can_return(self):
        """Check if this specific item is eligible for return."""
        if self.order_status != 3:  # Must be delivered
            return False
        if not getattr(self.order, "delivered_at", None):
            return False
        return_deadline = self.order.delivered_at + timedelta(days=self.RETURN_WINDOW_DAYS)
        return timezone.now() <= return_deadline
    
    @property
    def days_left_for_return(self):
        """Get days left for return for this specific item."""
        if not self.can_return:
            return 0
        return_deadline = self.order.delivered_at + timedelta(days=self.RETURN_WINDOW_DAYS)
        time_left = return_deadline - timezone.now()
        return max(0, time_left.days + (1 if time_left.seconds > 0 else 0))
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price
    
    class Meta:
        verbose_name_plural = "Order Items"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update parent order status after saving item
        self.order.update_order_status()