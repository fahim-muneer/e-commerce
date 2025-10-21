from django.db import models
from django.core.exceptions import ValidationError
from offer.models import Offers

class CategoryPage(models.Model):
    image = models.ImageField(upload_to='CategoryPage/')
    name = models.CharField(max_length=300, blank=False, unique=True)
    offer = models.ForeignKey(Offers, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'offer_type': 'category'})

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if CategoryPage.objects.exclude(pk=self.pk).filter(name__iexact=self.name).exists():  #pylint: disable=no-member
            raise ValidationError("Category with this name already exists (case-insensitive).")

    def __str__(self):
        return str(self.name)