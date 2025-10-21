from django.db import models
from django.core.exceptions import ValidationError
# Create your models here.

class Varient(models.Model):
    name=models.CharField(max_length=100 , unique=True ,blank=True,null=True)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    
    def clean(self):
        if Varient.objects.exclude(pk=self.pk).filter(name__iexact=self.name).exists():  #pylint: disable=no-member
            raise ValidationError("Category with this name already exists (case-insensitive).")
    
    def __str__(self):
        return str(self.name)
    
