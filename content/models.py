from datetime import datetime
from django.db import models
from django.utils.text import slugify
from ckeditor.fields import RichTextField

class StaticPage(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    content = RichTextField('Content', config_name='default')
    published = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first in menus")
    show_in_navbar = models.BooleanField(default=True, help_text="If checked, show in navbar")

    class Meta:
        ordering = ['order', 'title']  # Default ordering by order then title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    
    
    

class GalleryImage(models.Model):
    title = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='gallery/')
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title or f"Image {self.pk}"
    
    





class AboutPage(models.Model):
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to='about/', blank=True, null=True)
    section_image1 = models.ImageField(upload_to='about/', blank=True, null=True)
    section_image2 = models.ImageField(upload_to='about/', blank=True, null=True)
    section_image3 = models.ImageField(upload_to='about/', blank=True, null=True)
    section_image4 = models.ImageField(upload_to='about/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "About Page"
        verbose_name_plural = "About Page"

    def __str__(self):
        return self.title or "About Page"
    
    
    



class ContactPage(models.Model):
    title = models.CharField(max_length=255, default="Visit Our Store")
    address = models.TextField()
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    open_time = models.TextField(help_text="e.g., Every day 11am to 7pm")
    map_embed_url = models.TextField(help_text="Paste the Google Maps iframe `src` URL here")

    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    tiktok_url = models.URLField(blank=True, null=True)
    pinterest_url = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Contact Page"
        verbose_name_plural = "Contact Pages"

    def __str__(self):
        return "Contact Page"




class Location(models.Model):
    IN_STORE = 'in_store'
    OVERSEAS = 'overseas'
    LOCATION_TYPE_CHOICES = [
        (IN_STORE, 'In-Store'),
        (OVERSEAS, 'Overseas'),
    ]

    name = models.CharField(max_length=100)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"


class Appointment(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    referral_source = models.CharField(max_length=255)
    existing_customer = models.BooleanField(default=False)
    preferred_location = models.ForeignKey(
        Location,
        related_name='appointments',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    preferred_date = models.DateField(null=True, blank=True)  # New field
    preferred_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.preferred_location} on {self.preferred_date} at {self.preferred_time}"
    
    
    
    @property
    def preferred_datetime(self):
        if self.preferred_date and self.preferred_time:
            return datetime.combine(self.preferred_date, self.preferred_time)
        return None








class SocialMediaLink(models.Model):
    PLATFORM_CHOICES = [
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter'),
        ('instagram', 'Instagram'),
        ('linkedin', 'LinkedIn'),
        ('youtube', 'YouTube'),
        ('tiktok', 'TikTok'),
        ('pinterest', 'Pinterest'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    url = models.URLField()
    icon_class = models.CharField(max_length=100, help_text="Font Awesome class, e.g. 'fa fa-facebook' or custom SVG class.")
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.get_name_display()}"

