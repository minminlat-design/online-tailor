from django.db import models
from django.contrib.auth import get_user_model
from django.forms import ValidationError

User = get_user_model()

class MeasurementType(models.Model):
    name = models.CharField(max_length=50)  # e.g. "Chest"
    key = models.SlugField(unique=True)     # e.g. "chest"
    description = models.TextField(blank=True)
    video = models.FileField(upload_to='videos/%y/%m/%d/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="Controls display order")
    
    class Meta:
        ordering = ['order', 'name']  # ensures consistent order in admin/querysets

    def get_video_source(self):
        if self.video:
            return self.video.url
        return self.video_url

    def __str__(self):
        return self.name
    
    
    
class ProductType(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g. "shirt", "pants"

    def __str__(self):
        return self.name



class ProductTypeMeasurement(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE, related_name='measurements')
    measurement_type = models.ForeignKey(MeasurementType, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('product_type', 'measurement_type')
        
    
    def __str__(self):
       return f"{self.product_type.name} - {self.measurement_type.name}"






class UserMeasurement(models.Model):
    class FitType(models.TextChoices):
        REGULAR = 'tailor', 'Tailored Fit'
        SLIM = 'slim', 'Slim Fit'
        COMFORTABLE = 'comfortable', 'Comfortable Fit'
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='measurements')
    fit_type = models.CharField(
        max_length=20,
        choices=FitType.choices,
        default=FitType.REGULAR,
        help_text="Select the fit type for this measurement set."
    )
    measurement_data = models.JSONField()  # e.g. {"chest": 38.5, "waist": 32}

    photo_front = models.ImageField(upload_to="measurements/photos/%y/%m/%d/", blank=True, null=True)
    photo_side = models.ImageField(upload_to="measurements/photos/%y/%m/%d/", blank=True, null=True)
    photo_back = models.ImageField(upload_to="measurements/photos/%y/%m/%d/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    def clean(self):
        if not self.measurement_data:
            raise ValidationError("Measurement data is required and must be a dictionary.")

        if not isinstance(self.measurement_data, dict):
            raise ValidationError("Measurement data must be a dictionary.")

        for key, value in self.measurement_data.items():
            if not isinstance(value, (int, float)):
                raise ValidationError(f"Measurement '{key}' must be a number.")



    def __str__(self):
        return f"Measurement for {self.user} ({self.fit_type or self.created_at.strftime('%Y-%m-%d')})"
