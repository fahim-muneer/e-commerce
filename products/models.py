from django.db import models
from category.models import CategoryPage
# Create your models here.

class ProductPage(models.Model):
   
    image1=models.ImageField(upload_to='products/')
    image2=models.ImageField(upload_to='products/',blank=True)
    image3=models.ImageField(upload_to='products/',blank=True)
    image4=models.ImageField(upload_to='products/',blank=True)
    image5=models.ImageField(upload_to='products/',blank=True)
    name = models.CharField(max_length=300 ,blank=False , unique=False)
    description=models.TextField(max_length=1000)
    price=models.IntegerField()
    category = models.ForeignKey(CategoryPage , on_delete=models.CASCADE)
    priority = models.IntegerField(default = 0)
    old_price=models.IntegerField()
    block = models.BooleanField()
    stock = models.IntegerField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.name)
