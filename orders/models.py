from django.db import models
from django.contrib.auth import get_user_model
from measurement.models import UserMeasurement
from store.models import Product
from django.conf import settings

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True) 
    country = models.CharField(max_length=100, blank=True)  
    address = models.CharField(max_length=250)
    postal_code = models.CharField(max_length=20)
    city = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=250, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gift_wrap_fee  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    


    
    class Meta:
        ordering = ['-created']
        indexes = [
        models.Index(fields=['-created']),
        ]
        
    def __str__(self):
        return f'Order {self.id}'
    
    
    def items_subtotal(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_total_cost(self):
        return self.items_subtotal() + self.shipping_fee + self.gift_wrap_fee


    
    def get_stripe_url(self):
        if not self.stripe_id:
            return ''
        if '_test_' in settings.STRIPE_SECRET_KEY:
            path = '/test/'
        else:
            path = '/'
        return f'https://dashboard.stripe.com{path}payments/{self.stripe_id}'
    
        
    
    
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')

    product = models.ForeignKey(Product, on_delete=models.PROTECT)  # PROTECT to keep product reference
    product_name = models.CharField(max_length=255)  # freeze product name in case product changes later
    quantity = models.PositiveIntegerField()

    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    gift_wrap = models.BooleanField(default=False)
    user_measurement = models.ForeignKey(
        UserMeasurement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Reference to the original measurement set used (optional)."
    )

    frozen_measurement_data = models.JSONField(blank=True, null=True)

    selected_options = models.JSONField(default=dict, blank=True)
    customizations = models.JSONField(blank=True, null=True)
    
    
    def get_cost(self):
       return self.total_price


    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
