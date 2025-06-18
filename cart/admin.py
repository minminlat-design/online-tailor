from django.contrib import admin
from django.db import models
from .models import Cart, CartItem, CartSettings
from django_json_widget.widgets import JSONEditorWidget


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'date_added']


@admin.register(CartSettings)
class CartSettingsAdmin(admin.ModelAdmin):
    list_display = ('free_shipping_threshold', 'gift_wrap_price')




#cart items admin

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "cart",
        "quantity",
        "base_price",
        "total_price",
        "is_active",
        "user_measurement",
    )
    list_filter = ("is_active", "product")
    search_fields = ("product__name", "cart__id", "user_measurement__name")
    readonly_fields = ("total_price", "pretty_frozen_measurement_data")

    fieldsets = (
        (None, {
            "fields": (
                "product", "cart", "quantity", "is_active"
            )
        }),
        ("Pricing", {
            "fields": ("base_price", "total_price")
        }),
        ("Measurement", {
            "fields": (
                "user_measurement", 
                "pretty_frozen_measurement_data"
            )
        }),
        ("Customization & Options", {
            "fields": ("selected_options", "customizations")
        }),
    )

    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }

    def pretty_frozen_measurement_data(self, obj):
        import json
        if not obj.frozen_measurement_data:
            return "-"
        return json.dumps(obj.frozen_measurement_data, indent=2)
    pretty_frozen_measurement_data.short_description = "Frozen Measurement Data"
