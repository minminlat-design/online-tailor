from django.contrib import admin
from .models import TargetItem, VariationType, VariationOption

@admin.register(TargetItem)
class TargetItemAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(VariationType)
class VariationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']
    filter_horizontal = ['target_items'] # makes M2M easier to manage
    
@admin.register(VariationOption)
class VariationOptionAdmin(admin.ModelAdmin):
    list_display = ['type', 'name', 'order', 'included_by_default']
    list_filter = ['type']
    search_fields = ['name']
