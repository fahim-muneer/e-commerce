from django.db import models
from category.models import CategoryPage
from varients.models import Varient
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit
from offer.models import Offers
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
User = get_user_model()


class ProductPage(models.Model):
    
    image1 = models.ImageField(upload_to='products/')
    image1_thumbnail = ImageSpecField(
        source='image1',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85}
    )
    
    image2 = models.ImageField(upload_to='products/', blank=True)
    image2_thumbnail = ImageSpecField(
        source='image2',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85}
    )
    
    image3 = models.ImageField(upload_to='products/', blank=True)
    image3_thumbnail = ImageSpecField(
        source='image3',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85}
    )
    
    image4 = models.ImageField(upload_to='products/', blank=True)
    image4_thumbnail = ImageSpecField(
        source='image4',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85}
    )
    
    image5 = models.ImageField(upload_to='products/', blank=True)
    image5_thumbnail = ImageSpecField(
        source='image5',
        processors=[ResizeToFit(800, 800)],
        format='JPEG',
        options={'quality': 85}
    )
    
    name = models.CharField(max_length=300, blank=False, unique=False)
    description = models.TextField(max_length=1000)
    price = models.IntegerField(blank=True, null=True)
    old_price = models.IntegerField()
    stock = models.IntegerField(blank=True, null=True)
    priority = models.IntegerField(default=0)
    block = models.BooleanField(default=False)
    
    category = models.ForeignKey(CategoryPage, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offers, on_delete=models.SET_NULL, null=True, blank=True, 
                             limit_choices_to={'offer_type': 'product'})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.name)

    def get_active_offer(self):
        """Get the active offer for this product (product offer takes priority over category offer)"""
        now = timezone.now()
        
        if self.offer and self.offer.active:
            if self.offer.start_date <= now <= self.offer.end_date:
                return self.offer
        
        product_offer = Offers.objects.filter(
            products=self,  
            offer_type='product',  
            active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        if product_offer:
            return product_offer
        
        if self.category.offer and self.category.offer.active:
            if self.category.offer.start_date <= now <= self.category.offer.end_date:
                return self.category.offer
        
        category_offer = Offers.objects.filter(
            categories=self.category, 
            offer_type='category',  
            active=True,
            start_date__lte=now,
            end_date__gte=now
        ).first()
        
        return category_offer

    def calculate_discounted_price(self, original_price):
        if original_price is None:
            return Decimal('0.00')
        
        offer = self.get_active_offer()
        if offer:
            discount_amount = (Decimal(str(original_price)) * Decimal(str(offer.discount_percent))) / Decimal('100')
            discounted_price = Decimal(str(original_price)) - discount_amount
            return discounted_price
        
        return Decimal(str(original_price))

    def get_display_price(self):
        first_variant = self.variant.first()
        
        if first_variant and first_variant.price is not None:
            original_price = first_variant.price
        elif self.price is not None:
            original_price = self.price
        else:
            original_price = 0
        
        return self.calculate_discounted_price(original_price)

    def get_original_price(self):
        first_variant = self.variant.first()
        if first_variant and first_variant.price:
            return first_variant.price
        return self.price

    def get_discount_percentage(self):
        offer = self.get_active_offer()
        return offer.discount_percent if offer else 0

    def has_active_offer(self):
        return self.get_active_offer() is not None

    def has_stock(self):
        first_variant = self.variant.first()
        if first_variant:
            return first_variant.stock > 0 if first_variant.stock else False
        return self.stock > 0 if self.stock else False
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'


class ProductVariants(models.Model):
    product = models.ForeignKey(ProductPage, on_delete=models.CASCADE, related_name="variant")
    variant = models.ForeignKey(Varient, on_delete=models.CASCADE)
    stock = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    review = models.TextField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'variant')
    
    def get_price(self):
        return self.price if self.price else self.product.price
    
    def __str__(self):
        return f"{self.product.name} - {self.variant.name}"
    
    def get_discounted_price(self):
        original_price = self.price if self.price else self.product.price
        return self.product.calculate_discounted_price(original_price)

    def get_original_price(self):
        return self.price if self.price else self.product.price

    def has_active_offer(self):
        return self.product.has_active_offer()

    def get_discount_percentage(self):
        return self.product.get_discount_percentage()
    
    
class Review(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="reviews")
    product_variant=models.ForeignKey(ProductVariants,on_delete=models.CASCADE,related_name="reviews")
    comment=models.TextField(max_length=1000)
    rating = models.PositiveIntegerField(default=5)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together=('user','product_variant')
        
    def __str__(self):
        return f"{self.user.email} - {self.product_variant.product.name} ({self.rating})"

        