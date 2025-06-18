from django.contrib import admin
from .models import Order, OrderItem
from django.utils.safestring import mark_safe
import csv
import datetime
from django.http import HttpResponse
import json
from django.urls import reverse
from django.utils.html import format_html



def invoice_pdf(obj):
    url = reverse('orders:admin_order_invoice_pdf', args=[obj.id])
    return format_html('<a class="button" href="{}" target="_blank">🧾 Order PDF</a>', url)
invoice_pdf.short_description = "Invoice PDF"
    
        


 

def order_pdf(obj):
    url = reverse('orders:admin_order_pdf', args=[obj.id])
    return mark_safe(f'<a href="{url}">PDF</a>')
order_pdf.short_description = 'Invoice'



def order_detail(obj):
    url = reverse('orders:admin_order_detail', args=[obj.id])
    return mark_safe(f'<a href="{url}">View</a>')
    
    
    

def export_orders_with_items_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    response = HttpResponse(content_type='text/csv')
    filename = f"{opts.verbose_name_plural}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Header row - combine Order and OrderItem fields
    headers = [
        'Order ID', 'User', 'First Name', 'Last Name', 'Email', 'Phone',
        'Country', 'Address', 'Postal Code', 'City',
        'Created', 'Updated', 'Paid', 'Stripe ID', 'Status', 'Total Price',
        'Item Product Name', 'Item Quantity', 'Item Base Price', 'Item Total Price',
        'Gift Wrap',
        'User Measurement ID',
        'Frozen Measurement Data',
        'Selected Options',
        'Customizations',
    ]
    writer.writerow(headers)

    for order in queryset:
        order_created = order.created.strftime('%d/%m/%Y %H:%M')
        order_updated = order.updated.strftime('%d/%m/%Y %H:%M')

        for item in order.items.all():
            # Serialize JSON fields as compact JSON strings
            frozen_measurement = json.dumps(item.frozen_measurement_data, ensure_ascii=False) if item.frozen_measurement_data else ''
            selected_options = json.dumps(item.selected_options, ensure_ascii=False) if item.selected_options else ''
            customizations = json.dumps(item.customizations, ensure_ascii=False) if item.customizations else ''

            row = [
                order.id,
                order.user.email if order.user else '',
                order.first_name,
                order.last_name,
                order.email,
                order.phone,
                order.country,
                order.address,
                order.postal_code,
                order.city,
                order_created,
                order_updated,
                order.paid,
                order.stripe_id,
                order.status,
                order.total_price,
                item.product_name,
                item.quantity,
                item.base_price,
                item.total_price,
                item.gift_wrap,
                item.user_measurement.id if item.user_measurement else '',
                frozen_measurement,
                selected_options,
                customizations,
            ]
            writer.writerow(row)

    return response

export_orders_with_items_to_csv.short_description = 'Export Orders with Items to CSV'






def order_payment(obj):
    url = obj.get_stripe_url()
    if obj.stripe_id:
        html = f'<a href="{url}" target="_blank">{obj.stripe_id}</a>'
        return mark_safe(html)
    return ''

order_payment.short_description = 'Stripe Payment'



class OrderItemInline(admin.TabularInline):
    model = OrderItem
    readonly_fields = (
        'product', 'product_name', 'quantity',
        'base_price', 'total_price',
        'gift_wrap', 'user_measurement',
        'frozen_measurement_data',
        'selected_options', 'customizations'
    )
    can_delete = False
    extra = 0  # No empty extra forms

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created', 'paid', 'status', 'total_price', order_payment, order_detail, order_pdf, invoice_pdf)
    list_filter = ('paid', 'status', 'created')
    search_fields = ('id', 'user__email', 'email', 'first_name', 'last_name')
    readonly_fields = (
        'user', 'first_name', 'last_name', 'email',
        'phone', 'country',
        'address', 'postal_code', 'city',
        'created', 'updated', 'total_price'
    )
    inlines = [OrderItemInline]

    fieldsets = (
        ('Customer Info', {
            'fields': (
                'user', 'first_name', 'last_name', 'email', 'phone'
            )
        }),
        ('Shipping Info', {
            'fields': (
                'address', 'postal_code', 'city', 'country'
            )
        }),
        ('Status & Metadata', {
            'fields': (
                'paid', 'status', 'total_price', 'created', 'updated'
            )
        }),
    )
    
    actions = [export_orders_with_items_to_csv]
    
    
    
    
    