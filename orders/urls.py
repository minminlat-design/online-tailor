from django.urls import path
from orders import views, webhooks

app_name = 'orders'  # or 'checkout' if you prefer

urlpatterns = [
    path('shipping-info/', views.shipping_info_view, name='shipping_info'),
    #path('review/', views.checkout_review, name='checkout_review'),
    # later add your stripe checkout URL here, e.g.
    # path('payment/', views.stripe_checkout, name='payment'),
  
    path('shipping/', views.shipping_info_view, name='shipping_info'),
    path('review/', views.review_order_view, name='review_order'), 
    path('success/', views.payment_success_view, name='payment_success'),
    path('cancel/', views.payment_cancel_view, name='payment_cancel'),
    path('webhook/', webhooks.stripe_webhook, name='stripe-webhook'),
    
    
    #admin extension urls
    path('admin/order/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/order/<int:order_id>/pdf/', views.admin_order_pdf, name='admin_order_pdf'),
    path('admin/order/<int:order_id>/invoice-pdf/', views.admin_order_invoice_pdf, name='admin_order_invoice_pdf'),



]
