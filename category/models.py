from django.db import models

# Create your models here.
class CategoryPage(models.Model):
    name = models.CharField(max_length=300,blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return str(self.name)