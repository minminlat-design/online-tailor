from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    
    # Default main page
    path('', views.store, name='store'),
    
    
    # Main Category
    path('<slug:main_slug>/', views.store, name='store_main'),
    
    # Category
    path('<slug:main_slug>/<slug:category_slug>/', views.store, name='store_category'),
    
    # Sub Category
    path('<slug:main_slug>/<slug:category_slug>/<slug:subcategory_slug>/', views.store, name='store_subcategory'),
    
    # Product deatils
    path('<slug:main_slug>/<slug:category_slug>/<slug:subcategory_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
]
