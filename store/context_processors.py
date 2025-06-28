# core/context_processors.py  (or wherever you keep them)

from django.db.models import Count, Q, Prefetch
from store.models import Product, Brand          # adjust to your app label
from category.models import Category, MainCategory, SubCategory


def navbar_data(request):
    """
    One context-processor that supplies everything the header / sidebar needs,
    so each query runs only once per request.
    """
    
    brands = Brand.objects.all()

    # ---------- 1. Six random (or latest) products for the navbar dropdown
    navbar_products = (
        Product.objects
               .filter(is_available=True)
               .prefetch_related('images')[:6]        # LIMIT 6
    )

    # ---------- 2. Three categories for the top menu bar
    navbar_categories = (
        Category.objects
                .filter(is_active=True)
                .annotate(                      # total products in that category
                    product_count=Count(
                        'subcategories__products',
                        filter=Q(subcategories__products__is_available=True),
                        distinct=True
                    )
                )[2:5]                          # slice AFTER annotate
    )

   

    # ---------- 4. Full sidebar tree with counts
    links = (
        MainCategory.objects
            .prefetch_related(
                Prefetch(
                    'categories',
                    queryset=Category.objects
                        .filter(is_active=True)
                        .annotate(                 # count for “All”
                            product_count=Count(
                                'subcategories__products',
                                filter=Q(subcategories__products__is_available=True),
                                distinct=True
                            )
                        )
                        .prefetch_related(
                            Prefetch(
                                'subcategories',
                                queryset=SubCategory.objects.annotate(
                                    product_count=Count(
                                        'products',
                                        filter=Q(products__is_available=True)
                                    )
                                )
                            )
                        )
                )
            )
    )

    return {
        'navbar_products'     : navbar_products,
        'navbar_categories'   : navbar_categories,
        'brands'              : brands,
        'links'               : links,              # <<< used by your sidebar template
    }
