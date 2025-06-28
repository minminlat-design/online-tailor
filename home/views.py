from django.shortcuts import render
from .models import HomeSlider, LookBook, ShopGram
from category.models import Category
from store.models import Product, ReviewRating


def home(request):
    # home sliders
    sliders = HomeSlider.objects.filter(is_active=True)
    
    # shopy by category section
    shop_categories = Category.objects.filter(
        main_category__slug='shop',
        image__isnull=False
    ).select_related('main_category').order_by('name_order', 'name')[:6]
    
    # latest arrival product sections by shirt subcategory
    latest_products = Product.objects.filter(
        is_available=True,
        pieces__slug="shirt"
        ).order_by('-created_at')[:12] # limit for homepage
    
    # Lookbook section 
    lookbooks = LookBook.objects.filter(is_active=True).order_by('order', '-created_at')
    
    # Shop Gram section
    shop_gram_posts = ShopGram.objects.filter(is_active=True).prefetch_related('products').order_by('order', '-created_at')[:6]
    
    # In your existing home() view
    top_reviews = ReviewRating.objects.filter(
        status=True, parent__isnull=True  # only main reviews, not replies
    ).select_related('user', 'product') \
    .order_by('-created_at')[:5]  # Or order_by('-rating')[:5]
        
    
    context = {
        'sliders': sliders,
        'shop_categories': shop_categories,
        'latest_products': latest_products,
        'lookbooks': lookbooks,
        'shop_gram_posts': shop_gram_posts,
        'top_reviews': top_reviews,
    }
    
    
    return render(request, 'home.html', context)
