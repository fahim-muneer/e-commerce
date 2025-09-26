from django.db import models
from products.models import ProductPage
from customer.models import Register

# Create your models here.
class WishList(models.Model):
    user =models.ForeignKey(Register,on_delete=models.CASCADE)

class WishListItems(models.Model):
    wish_list=models.ForeignKey(WishList , on_delete=models.CASCADE)
    products=models.ForeignKey(ProductPage, on_delete=models.SET_NULL, null=True , blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
