from django.contrib import admin
from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase
from django.utils.html import format_html
from easy_thumbnails.files import get_thumbnailer
from store.models import (
    Product, ProductPiece, ProductVariation, Style,
    FabricCategory, Color,
    Season, Pattern, Material, ProductImage, ProductGroup,
    ReviewRating, ReviewReply, ProductFeature, MaterialCareItem, PieceSpec,
    Brand, ShippingFee
)





class ProductFeatureInline(admin.TabularInline):
    model = ProductFeature
    extra = 1

class MaterialCareItemInline(admin.TabularInline):
    model = MaterialCareItem
    extra = 1


class PieceSpecInline(admin.TabularInline):
    model = PieceSpec
    extra = 1







class ProductImageInline(SortableInlineAdminMixin, admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image_thumbnail', 'image', 'alt_text', 'order')
    ordering = ['order']
    readonly_fields = ('image_thumbnail',)
    show_change_link = True
    
    def image_thumbnail(self, obj):
        if obj.image:
            thumbnail_options = {'size': (80, 80), 'crop': True}
            thumb_url = get_thumbnailer(obj.image).get_thumbnail(thumbnail_options).url
            return format_html('<img src="{}" width="80" height="80" />', thumb_url)
        return "-"
    image_thumbnail.short_description = "Thumbnail"

# Product Variation Inline
class ProductVariationInline(admin.TabularInline):
    model = ProductVariation
    extra = 1
    autocomplete_fields = ['option']    
    
 
 
@admin.register(Product)
class ProductAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = [
        'name', 'is_customizable', 'group', 'sub_category',
        'price', 'weight', 'is_available', 'first_image_preview'
    ]
    list_filter = ['is_available', 'brand', 'group', 'sub_category', 'style']
    search_fields = ['name', 'description', 'brand__name', 'group__name']
    list_editable = ['price', 'weight', 'is_available']  # add weight here for inline editing
    prepopulated_fields = {'slug': ('name',)}
    inlines = [
        ProductImageInline, ProductVariationInline, ProductFeatureInline,
        MaterialCareItemInline, PieceSpecInline
    ]
    filter_horizontal = ['pieces']
    show_facets = admin.ShowFacets.ALWAYS

    def first_image_preview(self, obj):
        first_image = obj.images.order_by('order').first()
        if first_image and first_image.image:
            thumb_url = get_thumbnailer(first_image.image).get_thumbnail({'size': (50, 50), 'crop': True}).url
            return format_html('<img src="{}" width="50" height="50" />', thumb_url)
        return "-"
    
    first_image_preview.short_description = "Preview"

 
 
 


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


 
    

@admin.register(Style)
class StyleAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(FabricCategory)
class FabricCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    
@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ['name']
    
@admin.register(Pattern)
class PatternAdmin(admin.ModelAdmin):
    list_display = ['name']
    
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductGroup)
class ProductGroupAdmin(admin.ModelAdmin):
    list_display = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    
@admin.register(ProductVariation)
class ProductVariationAdmin(admin.ModelAdmin):
    list_display = ['product', 'option']
    list_filter = ['option__type', 'product__sub_category']
    search_fields = ['product__name', 'option__name']
    
    
@admin.register(ProductPiece)
class ProductPieceAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}




class ReviewReplyInline(admin.TabularInline):
    model = ReviewReply
    extra = 1  # show one empty form for adding new reply
    readonly_fields = ('created_at',)  # optional: prevent editing created_at

@admin.register(ReviewRating)
class ReviewRatingAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'subject', 'rating', 'status', 'created_at')
    search_fields = ('product__name', 'user__username', 'subject', 'review')
    list_filter = ('status', 'created_at')
    inlines = [ReviewReplyInline]

@admin.register(ReviewReply)
class ReviewReplyAdmin(admin.ModelAdmin):
    list_display = ('review', 'user', 'reply', 'created_at')
    search_fields = ('review__subject', 'user__username', 'reply')
    list_filter = ('created_at',)







@admin.register(ShippingFee)
class ShippingFeeAdmin(admin.ModelAdmin):
    list_display = [
        'min_weight', 'max_weight', 'min_fee', 'fee_per_kg', 'flat_fee'
    ]
    list_editable = [
        'min_fee', 'fee_per_kg', 'flat_fee'
    ]
    list_filter = ['min_weight', 'max_weight']
    search_fields = ['min_weight', 'max_weight']

    fieldsets = (
        (None, {
            'fields': ('min_weight', 'max_weight')
        }),
        ('Fee Details', {
            'fields': ('min_fee', 'fee_per_kg', 'flat_fee'),
            'description': 'Define the fees associated with this weight range.'
        }),
    )

    def has_add_permission(self, request):
        # Optionally, limit how many ShippingFee entries can be created
        return True  # or add logic if you want to restrict

    def has_delete_permission(self, request, obj=None):
        return True  # or add logic to restrict deleting if needed