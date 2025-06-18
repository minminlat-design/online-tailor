# content/admin.py

from django.contrib import admin
from .models import StaticPage,  GalleryImage, AboutPage, ContactPage
from django.utils.html import format_html
from easy_thumbnails.files import get_thumbnailer
from .models import Appointment, Location



@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'published')
    prepopulated_fields = {'slug': ('title',)}
    
    
    


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('thumbnail_preview', '__str__', 'is_visible', 'order', 'created_at')
    list_editable = ('is_visible', 'order')
    readonly_fields = ('thumbnail_preview',)

    def thumbnail_preview(self, obj):
        if obj.image:
            thumb_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 100), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="100" />', thumb_url)
        return "-"
    thumbnail_preview.short_description = 'Preview'
    
    





@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at', 'banner_preview')
    readonly_fields = ('updated_at', 'banner_preview')  # Don't include 'updated_at' in editable fields

    fieldsets = (
        (None, {
            'fields': ('title', 'content')
        }),
        ('Banner Section', {
            'fields': ('banner_image', 'banner_preview'),
        }),
        ('Extra Images', {
            'fields': ('section_image1', 'section_image2', 'section_image3', 'section_image4'),
        }),
        ('Metadata', {
            'fields': ('updated_at',),
        }),
    )

    def banner_preview(self, obj):
        if obj.banner_image:
            return format_html('<img src="{}" width="300" style="object-fit:cover;" />', obj.banner_image.url)
        return "(No image)"
    
    banner_preview.short_description = "Banner Preview"
    
    
    
    
    
    

@admin.register(ContactPage)
class ContactPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'email', 'phone', 'is_active']
    
    
    
@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_type', 'is_active')
    list_filter = ('location_type', 'is_active')
    search_fields = ('name',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'referral_source', 'existing_customer', 'preferred_location', 'submitted_at')
    list_filter = ('existing_customer', 'preferred_location')  # updated to singular FK
    search_fields = ('first_name', 'last_name', 'email', 'referral_source')
    # filter_horizontal removed because it works only for ManyToMany fields
    autocomplete_fields = ('preferred_location',)  # optional, for better FK selection UI
    date_hierarchy = 'submitted_at'
