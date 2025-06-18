from django.db import models

# Product variation start here >>>>>>>>>>>>>>

class VariationType(models.Model):
    name = models.CharField(max_length=100, unique=True) # lapel, Button, Vent, Lining
    description = models.TextField(blank=True, null=True)
    
    target_items = models.ManyToManyField('TargetItem', related_name='variation_types')
    
    def __str__(self):
        return self.name
    
class VariationOption(models.Model):
    type = models.ForeignKey(VariationType, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100, unique=True) # e.g., Lapel Style: Notch, 2 Buttons, Double Vents
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    included_by_default = models.BooleanField(default=False) # Optional
    image = models.ImageField(upload_to='variation_options/%Y/%m/%d/', blank=True, null=True)
    price_difference = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    class Meta:
        unique_together = ('type', 'name')
        ordering = ['type', 'order', 'name']
        
    def __str__(self):
        return f"{self.type.name} - {self.name}"


class TargetItem(models.Model):
    name = models.CharField(max_length=100, unique=True) # e.g. Jacket, Pants, Shirt
    
    def __str__(self):
        return self.name
    