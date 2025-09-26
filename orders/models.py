from django.db import models
from customer.models import Register
from category.models import CategoryPage
from products.models import ProductPage
from django.utils import timezone
from django.contrib.auth import get_user_model
User = get_user_model()

# Create your models here.


# class OrderStatus(models.Model):
#     name        = models.CharField(max_length=300 , unique=True)
#     created_at  = models.DateTimeField(auto_now_add=True)
    



class OrderAddress(models.Model):
    user       = models.ForeignKey(Register,on_delete=models.CASCADE, null=True , blank=True)
    mobile     = models.CharField  (max_length=20 , blank=False , unique=False)
    second_mob = models.CharField  (max_length=20 , blank=True ,  unique=False)
    address    = models.CharField  (max_length=500 , blank=False  )
    city       = models.CharField  (max_length=300 , blank=False)
    state      = models.CharField  (max_length=200 , blank=False)
    pin        = models.IntegerField()
    country    = models.CharField  (max_length=100 , blank=False)
    created_at = models.DateTimeField(null=True, blank=True)
    
    

    
# class OrderDetails(models.Model):
#     order_info   = models.ForeignKey(Orders , on_delete=models.CASCADE)
#     order_status = models.ForeignKey(OrderStatus , on_delete=models.CASCADE)
#     created_at   = models.DateTimeField(auto_now_add=True)
    
class Cart(models.Model):
    owner           = models.OneToOneField(User,on_delete=models.SET_NULL,null=True,related_name='cart')
    CART_STAGE      = 0
    ORDER_CONFIRMED = 1
    ORDER_PROCESSED = 2
    ORDER_DELIVERED = 3
    ORDER_REJECTED  = 4
    STATUS_CHOICE   = ((CART_STAGE, 'CART_STAGE'),  
                       (ORDER_PROCESSED,'ORDER_PROCESSED'),
                       (ORDER_CONFIRMED,'ORDER_CONFIRMED'),
                       (ORDER_DELIVERED, 'ORDER_DELIVERED'),
                       (ORDER_REJECTED,'ORDER_REJECTED'))
    order_status = models.IntegerField(choices=STATUS_CHOICE,default=CART_STAGE)
    created_at      = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return f"Cart for {self.owner.email if self.owner else 'Anonymous'}"    #pylint: disable=no-member
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.ordered_items.all())   #pylint: disable=no-member
    
    @property
    def total_price(self):
        return sum(item.quantity * item.product.price for item in self.ordered_items.all() if item.product)   #pylint: disable=no-member

 

class CartItems(models.Model):
    product    = models.ForeignKey(ProductPage,on_delete=models.SET_NULL,null=True,related_name="cart_item")
    quantity   = models.IntegerField(default=1)
    owner      = models.ForeignKey(Cart , on_delete=models.CASCADE,related_name='ordered_items')
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    class Meta:
            unique_together = ('product', 'owner')  
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name if self.product else 'Deleted Product'}"
    
    @property
    def item_total(self):
        if self.product:
            return self.quantity * self.product.price  #pylint: disable=no-member
        return 0

class Coupons(models.Model):
    user=models.ForeignKey(Register , on_delete=models.CASCADE)
    code=models.CharField(max_length=10)
    disciptions=models.TextField()
    ACTIVE= 0
    INACTIVE=1
    STATUS_CHOICE=((ACTIVE,'ACTIVE'),
                   (INACTIVE,'INACTIVE'))
    status=models.IntegerField(choices=STATUS_CHOICE,default=INACTIVE)
    expir_at=models.DateTimeField()
    created_at      = models.DateTimeField(auto_now_add=True)

    

class Orders(models.Model):
    user             = models.ForeignKey(Register, on_delete=models.SET_NULL, null=True)
    delivery_address = models.ForeignKey(OrderAddress, on_delete=models.SET_NULL, null=True)

    
    CASH_ON_DELIVERY = 0
    ONLINE_PAYMENT   = 1
    PAYMENT_CHOICES = (
        (CASH_ON_DELIVERY, "Cash on Delivery"),
        (ONLINE_PAYMENT, "Online Payment"),
    )
    payment_method = models.IntegerField(choices=PAYMENT_CHOICES, default=CASH_ON_DELIVERY)

    
    PENDING = 0
    PAID    = 1
    PAYMENT_STATUS_CHOICES = (
        (PENDING, "Pending"),
        (PAID, "Paid"),
    )
    payment_status = models.IntegerField(choices=PAYMENT_STATUS_CHOICES, default=PENDING)

    
    STATUS_CHOICES = (
        (0, "Pending"),
        (1, "Confirmed"),
        (2, "Processed"),
        (3, "Delivered"),
        (4, "Rejected"),
    )
    order_status = models.IntegerField(choices=STATUS_CHOICES, default=0)
    return_reason=models.TextField(max_length=500,null=True , blank=True )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code  = models.ForeignKey(Coupons, on_delete=models.SET_NULL, null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Order #{self.id} by {self.user}"   #pylint: disable=no-member


class OrderItem(models.Model):
    order = models.ForeignKey(Orders, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ProductPage, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) 
    created_at      = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Order Items"
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order #{self.order.id}"       #pylint: disable=no-member
    
    @property
    def total_price(self):
        return self.quantity * self.unit_price


