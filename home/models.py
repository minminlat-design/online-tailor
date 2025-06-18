from django.db import models

from store.models import Product


class HomeSlider(models.Model):
    name = models.CharField(max_length=100)
    short_description = models.CharField(max_length=255, blank=True)
    image = models.ImageField(upload_to='home/home_slider/%Y/%m/%d/')
    alt_text = models.CharField(max_length=150)
    url = models.CharField(max_length=255, default='/store/shop/', blank=True)
    button_text = models.CharField(max_length=50, default='Shop Collection', blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True) # To toggle visibility
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        
    def __str__(self):
        return self.name

# Look book section    
class LookBook(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='lookbook/%Y/%m/%d/')
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True) # To toggle visibility
    
    
    class Meta:
        ordering = ['order', '-created_at']
    
    
    def __str__(self):
        return self.name
    
# Shop Gram
class ShopGram(models.Model):
    caption = models.CharField(max_length=255, blank=True)
    image =  models.ImageField(upload_to='shopgram/%Y/%m/%d/')
    products = models.ManyToManyField(Product, related_name='shopgram_posts')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveSmallIntegerField(default=0)
    source_url = models.URLField(blank=True, null=True) 
    
    class Meta:
        ordering = ['order', '-created_at']
        
    def __str__(self):
        return self.caption or f"Post {self.pk}"
        
        
    
    
    
    
    