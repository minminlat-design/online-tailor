from django.contrib import admin
from .models import MainCategory, Category, SubCategory
from easy_thumbnails.files import get_thumbnailer
from django.utils.html import format_html

@admin.register(MainCategory)
class MainCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    
    ordering = ['name']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['main_category', 'admin_thumbnail', 'name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    
    ordering = ['main_category', 'name']
    
    
    def admin_thumbnail(self, obj):
        if obj.image:
            thumbnail_url = get_thumbnailer(obj.image).get_thumbnail({'size': (100, 60), 'crop': True}).url
            return format_html('<img src="{}" width="100" height="auto" />', thumbnail_url)
        return "No image"
    
    admin_thumbnail.short_description = "Image"
    
    

@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['category', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    
    ordering = ['category', 'name']
    

