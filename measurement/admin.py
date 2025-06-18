from django.contrib import admin
from .models import (
    MeasurementType,
    ProductType,
    ProductTypeMeasurement,
    UserMeasurement
)

# Optional: pretty JSON formatting
import json
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


@admin.register(MeasurementType)
class MeasurementTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "order", "has_video")
    list_editable = ("order",)  # allows inline editing of 'order' in the list view
    search_fields = ("name", "key")
    readonly_fields = ("video_preview",)
    prepopulated_fields = {'key': ('name',)}  # prepopulate 'key' from 'name'

    def has_video(self, obj):
        return bool(obj.video or obj.video_url)
    has_video.boolean = True

    def video_preview(self, obj):
        url = obj.get_video_source()
        if url:
            return format_html('<video width="300" controls><source src="{}" type="video/mp4">Your browser does not support video.</video>', url)
        return "No video available"


class ProductTypeMeasurementInline(admin.TabularInline):
    model = ProductTypeMeasurement
    extra = 1


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    inlines = [ProductTypeMeasurementInline]


@admin.register(ProductTypeMeasurement)
class ProductTypeMeasurementAdmin(admin.ModelAdmin):
    list_display = ("product_type", "measurement_type")
    list_filter = ("product_type",)


@admin.register(UserMeasurement)
class UserMeasurementAdmin(admin.ModelAdmin):
    list_display = ("user", "fit_type", "created_at", "updated_at")
    search_fields = ("user__username", "fit_type")
    readonly_fields = ("created_at", "updated_at", "pretty_measurement_data", "photo_preview")

    def pretty_measurement_data(self, obj):
        if not obj.measurement_data:
            return "-"
        return format_html(
            "<pre>{}</pre>",
            json.dumps(obj.measurement_data, indent=2)
        )
    pretty_measurement_data.short_description = "Measurement Data"

    def photo_preview(self, obj):
        imgs = []
        for field in ['photo_front', 'photo_side', 'photo_back']:
            photo = getattr(obj, field)
            if photo:
                imgs.append(f'<img src="{photo.url}" height="150" style="margin: 5px;" />')
        return mark_safe("".join(imgs)) if imgs else "No photos"
    photo_preview.short_description = "Photos"
