from django.contrib import admin
from .models import Coupon

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code',
        'valid_from',
        'valid_to',
        'discount',
        'active',
        'used_count',     # ← show how many times it's been used
        'usage_limit'     # ← show the max allowed usages
    ]
    list_filter = ['active', 'valid_from', 'valid_to']
    search_fields = ['code']
