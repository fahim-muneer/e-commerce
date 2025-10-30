from django.db import models

# Create your models here.
class Banner(models.Model):
    name = models.CharField(max_length=100,blank=False,unique=True)
    image= models.ImageField(upload_to='banner/')
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
