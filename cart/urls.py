from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),  # View full cart page
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),  # Add item (supports JSON and form POST)
    path('remove/<int:product_id>/', views.cart_remove, name='cart_remove'),  # Remove item
    path('update-quantity/', views.cart_update_quantity, name='cart_update_quantity'),  # AJAX: update quantity
    path('shipping-info/', views.cart_shipping_info, name='cart_shipping_info'),  # AJAX: free shipping progress
    path('toggle-gift-wrap/', views.toggle_gift_wrap, name='toggle_gift_wrap'),  # AJAX: toggle gift wrap
    path('checkout/', views.cart_to_checkout, name='cart_to_checkout'),
    path('measurement/', views.measurement_form_view, name='measurement_form_view'),
]
