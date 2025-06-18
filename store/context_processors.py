from .models import Product
from category.models import Category

def products_for_navbar(request):
    products = Product.objects.filter(is_available=True).prefetch_related('images')[:6] # limited to 6
    return {
        'navbar_products': products,
    }
    

def categories_for_navbar(request):
    categories = Category.objects.filter(is_active=True)[2:5]
    return {
        'navbar_categories': categories,
    }
    
def trunk_shows_navbar(request):
    trunk_shows = Product.objects.filter(is_available=True).prefetch_related('images')[:2]
    return {
        'navbar_trunk_shows': trunk_shows,
    }