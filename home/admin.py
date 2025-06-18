from django.contrib import admin
from .models import HomeSlider, LookBook, ShopGram
from easy_thumbnails.files import get_thumbnailer
from django.utils.html import format_html


@admin.register(HomeSlider)
class HomeSliderAdmin(admin.ModelAdmin):
    list_display = ['admin_thumbnail', 'name', 'alt_text', 'url', 'button_text', 'is_active', 'created_at']
    list_filter = ['is_active',]
    search_fields = ['name', 'alt_text', 'short_description']
    prepopulated_fields = {'alt_text': ('name',)}
    
    def admin_thumbnail(self, obj):
        if obj.image:
            thumbnail_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 60), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="auto" />', thumbnail_url)
        return "No image"
    
    admin_thumbnail.short_description = "Image"



# lookbook admin
@admin.register(LookBook)
class LookBookAdmin(admin.ModelAdmin):
    list_display = ['admin_thumbnail', 'name', 'created_at', 'is_active']
    list_filter = ['is_active',]
    search_fields = ['name']
    
    def admin_thumbnail(self, obj):
        if obj.image:
            thumbnail_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 60), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="auto" />', thumbnail_url)
        return "No image"
    
    admin_thumbnail.short_description = "Image"
    



# Shop Gram admin    
@admin.register(ShopGram)
class ShopGramAdmin(admin.ModelAdmin):
    list_display = ['admin_thumbnail', 'caption', 'created_at', 'is_active']
    list_filter = ['is_active']
    search_fields = ['caption']  # corrected from 'name' unless you have a 'name' field
    fields = ['caption', 'image', 'products', 'source_url', 'is_active', 'order']  # ✅ include source_url

    def admin_thumbnail(self, obj):
        if obj.image:
            thumbnail_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 60), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="auto" />', thumbnail_url)
        return "No image"
    
    admin_thumbnail.short_description = "Image"


