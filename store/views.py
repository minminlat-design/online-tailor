from django.shortcuts import get_object_or_404, render
from cart.forms import CartAddProductForm
from category.models import MainCategory, Category, SubCategory
from store.models import Product, ProductImage
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from collections import defaultdict
from django.utils.text import slugify
from variation.models import VariationType




def store(request, main_slug=None, category_slug=None, subcategory_slug=None):
    main_category = None
    category = None
    sub_category = None
    subcategories = None
    categories = None
    products = Product.objects.filter(is_available=True)
    active_main_category_id = None

    if main_slug and category_slug and subcategory_slug:
        # Filter by subcategory
        sub_category = get_object_or_404(SubCategory, 
            slug=subcategory_slug, 
            category__slug=category_slug, 
            category__main_category__slug=main_slug
        )
        category = sub_category.category
        main_category = category.main_category
        products = products.filter(sub_category=sub_category)
        active_main_category_id = main_category.id

        # annotate all categories for sidebar
        categories = main_category.categories.prefetch_related(
            Prefetch(
                'subcategories',
                queryset=SubCategory.objects.annotate(
                    product_count=Count('products', filter=Q(products__is_available=True))
                )
            )
        ).annotate(
            product_count=Count('subcategories__products', filter=Q(subcategories__products__is_available=True), distinct=True)
        )

    elif main_slug and category_slug:
        # Filter by category
        category = get_object_or_404(Category, slug=category_slug, main_category__slug=main_slug)
        main_category = category.main_category
        active_main_category_id = main_category.id

        # annotate subcategories of current category
        subcategories = category.subcategories.annotate(
            product_count=Count('products', filter=Q(products__is_available=True))
        )
        products = products.filter(sub_category__in=subcategories)

        # annotate all categories for sidebar
        categories = main_category.categories.prefetch_related(
            Prefetch(
                'subcategories',
                queryset=SubCategory.objects.annotate(
                    product_count=Count('products', filter=Q(products__is_available=True))
                )
            )
        ).annotate(
            product_count=Count('subcategories__products', filter=Q(subcategories__products__is_available=True), distinct=True)
        )

    elif main_slug:
        # Filter by MainCategory
        main_category = get_object_or_404(MainCategory, slug=main_slug)
        active_main_category_id = main_category.id

        categories = main_category.categories.prefetch_related(
            Prefetch(
                'subcategories',
                queryset=SubCategory.objects.annotate(
                    product_count=Count('products', filter=Q(products__is_available=True))
                )
            )
        ).annotate(
            product_count=Count('subcategories__products', filter=Q(subcategories__products__is_available=True), distinct=True)
        )

        all_subcategories = SubCategory.objects.filter(category__main_category=main_category)
        products = products.filter(sub_category__in=all_subcategories)
        
        
    sale_products = Product.is_sale.all()[:3]  # fetch sale products
    gallery = Product.objects.filter(is_available=True)[:6]  # Shop sidebar gallery


    context = {
        'main_category': main_category,
        'category': category,
        'sub_category': sub_category,
        'subcategories': subcategories,
        'products': products,
        'active_category_id': category.id if category else None,
        'active_main_category_id': active_main_category_id,
        'categories': categories,  # includes prefetched subcategories with product_count
        'sale_products': sale_products,
        'gallery': gallery,
    }

    return render(request, 'store/store.html', context)




# Product detail page

def product_detail(request, main_slug, category_slug, subcategory_slug, product_slug):
    product = get_object_or_404(
        Product,
        slug=product_slug,
        sub_category__slug=subcategory_slug,
        sub_category__category__slug=category_slug,
        sub_category__category__main_category__slug=main_slug
    )
    
    product_pieces = [piece.name.lower() for piece in product.pieces.all()]

    # Fetch all related variations with their option and type
    variations = product.variations.prefetch_related(
        'option__type',
        'option__type__target_items'
    )
    
    monogram_price = None
    vest_price = None
    shirt_price = None
    

    set_items = []
    
    customization_by_target = defaultdict(lambda: defaultdict(list))
    
    set_items_unsorted = []
    
    for variation in variations:
      print(f"Option ID: {variation.option.id}, Name: {variation.option.name}, Variation price_difference: {variation.price_difference}")


    for variation in variations:
        option = variation.option
        vtype = option.type
        option.price_difference = variation.price_difference
        
        
        
        # Store target names to help frontend rendering (e.g., 'jacket', 'vest')
        option.target_names = [target.name.lower() for target in vtype.target_items.all()]
        
        # Extract Monogrm price
        if vtype.name.lower() == "monogram" and monogram_price is None:
            monogram_price = variation.price_difference
            
        
            
        # Extract Vest price
        if vtype.name.lower() == "vest" and option.name.lower() == "vest" and vest_price is None:
            vest_price = variation.price_difference
            
        # Extract Shirt price
        if vtype.name.lower() == "shirt" and option.name.lower() == "shirt" and shirt_price is None:
            shirt_price = variation.price_difference

        # If this is the "Set Items" variation type (e.g., Jacket, Pants, Shirt), collect it
        if vtype.name.lower() == 'set items':
            set_items_unsorted.append(option)
            
        else:
            for target in vtype.target_items.all():
                key = slugify(vtype.name).replace('-', ' ')  # e.g., lapel
                target_name = target.name.strip().lower()
                print(f"{target_name}- {key} -> {option.name}")
                customization_by_target[target.name.lower()][key].append(option)
                
    # Sort set_items by VariationOption.order
    set_items = sorted(set_items_unsorted, key=lambda o: o.order)

    cart_product_form = CartAddProductForm()

    images = ProductImage.objects.filter(product=product).select_related('color').order_by('order')

    timer = 0
    if product.countdown_end:
        remaining = (product.countdown_end - timezone.now()).total_seconds()
        timer = max(int(remaining), 0)
        
    monogram_keys = ["monogram_style", "monogram_color", "monogram_placement", "shirt_monogram_placement",
                     "shirt_monogram_color", "shirt_monogram_style"]
    
    
    if request.method == "POST":
        for key in request.POST:
            if key.startswith(('jacket-', 'pants-', 'shirt-', 'vest-', 'monogram')):
                values = request.POST.getlist(key)
                print(f"Selected for {key}: {values}")

        
    

        
    
    
    

    context = {
        'product': product,
        'images': images,
        'first_image': product.first_image(),
        'timer': timer,
        'cart_product_form': cart_product_form,
        'set_items': set_items,
        'customizations': {
            k: dict(v) for k, v in customization_by_target.items()
        },  # { "jacket": { "lapel": [...], "vent": [...] }, ... }
        'variations': variations,  # To check "included_by_default" in the template
        'product_pieces': product_pieces,
        'monogram_keys': monogram_keys,
        
        'monogram_price': monogram_price or 0,
        
        'vest_price': vest_price or 0,
        'shirt_price': shirt_price or 0,
        
    }
    
    # Determine which item pieces are included in this product
    included_pieces = {
        'is_jacket_product': product.pieces.filter(name__iexact="jacket").exists(),
        'is_vest_product': product.pieces.filter(name__iexact="vest").exists(),
        'is_pants_product': product.pieces.filter(name__iexact="pants").exists(),
        'is_shirt_product': product.pieces.filter(name__iexact="shirt").exists(),
    }

    context.update(included_pieces)


    return render(request, 'store/product_detail.html', context)


