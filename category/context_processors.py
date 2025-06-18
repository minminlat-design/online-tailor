from category.models import MainCategory, Category, SubCategory
from store.models import Product
from django.db.models import Count, Prefetch, Q


def menu_links(request):
    links = MainCategory.objects.prefetch_related(
        Prefetch(
            'categories',
            queryset=Category.objects.prefetch_related(
                Prefetch(
                    'subcategories',
                    queryset=SubCategory.objects.annotate(
                        product_count=Count('products', filter=Q(products__is_available=True))
                    )
                )
            )
        )
        
    )
    return dict(links=links)