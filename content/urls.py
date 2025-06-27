from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    # Specific URLs first
    path('make-an-appointment/success/', views.make_appointment_success, name='make_appointment_success'),
    path('contact/submit/', views.contact_form_view, name='contact_form'),

    # General slug match last
    path('<slug:slug>/', views.static_page_detail, name='static_page_detail'),
    
    # Add these two static page routes
    path('shipping-delivery/', views.static_page_detail, {'slug': 'shipping-delivery'}, name='shipping_delivery'),
    path('delivery-return/', views.static_page_detail, {'slug': 'delivery-return'}, name='delivery_return'),
    path('privacy-policy/', views.static_page_detail, {'slug': 'privacy-policy'}, name='privacy_policy'),
    path('terms-conditions/', views.static_page_detail, {'slug': 'terms-and-conditions'}, name='terms_conditions'),
    path('faq/', views.static_page_detail, {'slug': 'faq'}, name='faq'),
    
]
