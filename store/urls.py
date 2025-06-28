from django.urls import path
from . import views

app_name = 'store'

urlpatterns = [
    # Product image ranking
    path('image-ranking/', views.image_ranking, name='image_ranking'),

    # Action-based routes — these must go FIRST
    path('submit_review/<int:product_id>/', views.submit_review, name='submit_review'),
    path('submit-reply/<int:review_id>/', views.submit_reply, name='submit_reply'),

    # ↓↓↓ SEO-friendly filter URLs go BEFORE catch-all slugs ↓↓↓
    path("shop/", views.store, name="store_all"),
    path("shop/brand/<slug:brand_slug>/", views.store, name="store_brand"),
    path("shop/color/<slug:color_slug>/", views.store, name="store_color"),
    path("shop/brand/<slug:brand_slug>/color/<slug:color_slug>/", views.store, name="store_brand_color"),

    # Product detail
    path('<slug:main_slug>/<slug:category_slug>/<slug:subcategory_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),

    # Sub Category
    path('<slug:main_slug>/<slug:category_slug>/<slug:subcategory_slug>/', views.store, name='store_subcategory'),

    # Category
    path('<slug:main_slug>/<slug:category_slug>/', views.store, name='store_category'),

    # Main Category
    path('<slug:main_slug>/', views.store, name='store_main'),

    # Default store page
    path('', views.store, name='store'),
]
