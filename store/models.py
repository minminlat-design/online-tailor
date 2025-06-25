from django.db import models
from django.urls import reverse
from accounts.models import Account
from category.models import SubCategory
from django.forms import ValidationError
from ckeditor.fields import RichTextField
from django.db.models import F
from django.db.models import Avg
from measurement.models import ProductType


class IsSaleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            discounted_price__isnull=False,
            discounted_price__lt=F('price')
        )



class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    
    group = models.ForeignKey('ProductGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    sub_category = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products') # must not use '' cos it is imported from another app
    
    description = RichTextField('Description', config_name='default')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    delivery_days = models.PositiveIntegerField(default=7)
    
    style = models.ForeignKey('Style', on_delete=models.SET_NULL, null=True, blank=True)  # For suit, jacket, pants styles
    color = models.ForeignKey('Color', on_delete=models.SET_NULL, null=True, blank=True)  # Default/primary color
    material = models.ForeignKey('Material', on_delete=models.SET_NULL, null=True, blank=True)
    pattern = models.ForeignKey('Pattern', on_delete=models.SET_NULL, null=True, blank=True)
    season = models.ForeignKey('Season', on_delete=models.SET_NULL, null=True, blank=True)
    occasion = models.ForeignKey('FabricCategory', on_delete=models.SET_NULL, null=True, blank=True)
    is_customizable = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    countdown_end = models.DateTimeField(null=True, blank=True) # Countdown ends at this date
    
    pieces = models.ManyToManyField('ProductPiece', blank=True, related_name='products')
    
    objects = models.Manager() # default manager
    is_sale = IsSaleManager() # Custom manager for sale products
    # measuring type field
    product_type = models.ForeignKey(ProductType, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
   
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['name']),
            models.Index(fields=['-created_at']),
        ]
        
    
    def clean(self):
        if self.discounted_price and self.discounted_price >= self.price:
            raise ValidationError("Discounted price must be less than original price.")


    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse(
            'store:product_detail',
            args=[
                self.sub_category.category.main_category.slug,
                self.sub_category.category.slug,
                self.sub_category.slug,
                self.slug
            ]
        )
        
    def first_image(self):
        return self.images.order_by('order').first()
    
    def second_image(self):
        images = self.images.order_by('order')
        return images[1] if images.count() > 1 else None
    
    
    @property
    def average_rating(self):
        avg = self.reviews.filter(status=True).aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg * 2) / 2 if avg else 0  # rounds to nearest 0.5
    
    @property
    def total_reviews(self):
        return self.reviews.filter(status=True).count()

    
    

class Style(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., Slim Fit, Classic Fit
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.name
    

    
class Season(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. All-Season, Summer, Winter
    
    def __str__(self):
        return self.name
    
class Pattern(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., Plain, Stripe, Check
    
    def __str__(self):
        return self.name
    
class Material(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. Wool, linen
    
    def __str__(self):
        return self.name
    
class FabricCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., Business, Wedding
    
    class Meta:
        verbose_name_plural = "Fabric Categories"
    
    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., Navy Blue
    hex_code = models.CharField(max_length=7, blank=True, null=True)  # e.g., #000080 for frontend use
    image = models.ImageField(upload_to='colors/', blank=True, null=True)  # optional swatch

    def __str__(self):
        return self.name

# will use this for future product
class ProductGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    
    def __str__(self):
        return self.name
    
class ProductImage(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='products/gallery/%Y/%m/%d')
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order'] # Ensures images are always ordered
    
    def __str__(self):
        return f"{self.product.name} - {self.alt_text or 'Image'}"


#  Connect Variations to Products
class ProductVariation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variations')
    option = models.ForeignKey('variation.VariationOption', on_delete=models.CASCADE)
    price_difference = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    
    class Meta:
        unique_together = ('product', 'option')
        
    def __str__(self):
        return f"{self.product.name} - {self.option.name}"
    
    
# This will store entries like: 'Jacket', 'Pants', 'Vest', 'Shirt', etc
class ProductPiece(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Product Piece'
        verbose_name_plural = 'Product Pieces'
        
    def __str__(self):
        return self.name
    
    



# Review rating
class ReviewRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100, blank=True)
    review = models.TextField(max_length=500, blank=True)
    rating = models.FloatField()
    ip = models.GenericIPAddressField(blank=True, null=True)  # better for storing IPs
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
     # Add a self-referential ForeignKey for replies
    parent = models.ForeignKey('self', null=True, blank=True, related_name='child_reviews', on_delete=models.CASCADE)


    def __str__(self):
        return self.subject or f"Review by {self.user} on {self.product}"
    
    
    
# Review reply
class ReviewReply(models.Model):
    review = models.ForeignKey(ReviewRating, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    reply = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply by {self.user} on {self.review}"
