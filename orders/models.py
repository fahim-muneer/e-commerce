from django.db import models
from custom_admin.models import Register
from category.models import CategoryPage

# Create your models here.


class OrderStatus(models.Model):
    name = models.CharField(max_length=300 , unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    



class OrderAddress(models.Model):
    mobile     = models.CharField  (max_length=20 , blank=False , unique=False)
    second_mob = models.CharField  (max_length=20 , blank=True ,  unique=False)
    address    = models.CharField  (max_length=500 , blank=False  )
    city       = models.CharField  (max_length=300 , blank=False)
    state      = models.CharField  (max_length=200 , blank=False)
    pin        = models.IntegerField()
    country    = models.CharField  (max_length=100 , blank=False)

class Orders(models.Model):
    user                = models.ForeignKey     (Register     , on_delete=models.CASCADE)
    delivery_address    = models.ForeignKey     (OrderAddress , on_delete=models.CASCADE)
    category            = models.ForeignKey     (CategoryPage , on_delete=models.CASCADE)
    ordered_at          = models.DateTimeField  (auto_now_add=True)
    
    
class OrderDetails(models.Model):
    order_info = models.ForeignKey(Orders , on_delete=models.CASCADE)
    order_status= models.ForeignKey(OrderStatus , on_delete=models.CASCADE)
    created_at =models.DateTimeField(auto_now_add=True)