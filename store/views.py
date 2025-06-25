from django.shortcuts import get_object_or_404, redirect, render
from cart.forms import CartAddProductForm
from category.models import MainCategory, Category, SubCategory
from store.forms import ReviewRatingForm, ReviewReplyForm
from store.models import Product, ProductImage, ReviewRating
from django.db.models import Count, Q, Prefetch
from django.utils import timezone
from collections import defaultdict
from django.utils.text import slugify
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from .models import ReviewRating
from django.db.models import Avg, Count
from collections import defaultdict as dd  # alias to avoid conflict with customization_by_target
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string







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







def product_detail(request, main_slug, category_slug, subcategory_slug, product_slug):
    product = get_object_or_404(
        Product,
        slug=product_slug,
        sub_category__slug=subcategory_slug,
        sub_category__category__slug=category_slug,
        sub_category__category__main_category__slug=main_slug
    )
    
    product_pieces = [piece.name.lower() for piece in product.pieces.all()]

    variations = product.variations.prefetch_related(
        'option__type',
        'option__type__target_items'
    )
    
    monogram_price = None
    vest_price = None
    shirt_price = None
    
    set_items_unsorted = []
    customization_by_target = defaultdict(lambda: defaultdict(list))
    
    for variation in variations:
        option = variation.option
        vtype = option.type
        option.price_difference = variation.price_difference
        
        option.target_names = [target.name.lower() for target in vtype.target_items.all()]
        
        if vtype.name.lower() == "monogram" and monogram_price is None:
            monogram_price = variation.price_difference
            
        if vtype.name.lower() == "vest" and option.name.lower() == "vest" and vest_price is None:
            vest_price = variation.price_difference
            
        if vtype.name.lower() == "shirt" and option.name.lower() == "shirt" and shirt_price is None:
            shirt_price = variation.price_difference

        if vtype.name.lower() == 'set items':
            set_items_unsorted.append(option)
        else:
            for target in vtype.target_items.all():
                key = slugify(vtype.name).replace('-', ' ')
                customization_by_target[target.name.lower()][key].append(option)
                
    set_items = sorted(set_items_unsorted, key=lambda o: o.order)

    cart_product_form = CartAddProductForm()

    images = ProductImage.objects.filter(product=product).select_related('color').order_by('order')

    timer = 0
    if product.countdown_end:
        remaining = (product.countdown_end - timezone.now()).total_seconds()
        timer = max(int(remaining), 0)
        
    monogram_keys = [
        "monogram_style", "monogram_color", "monogram_placement",
        "shirt_monogram_placement", "shirt_monogram_color", "shirt_monogram_style"
    ]

    if request.method == "POST":
        for key in request.POST:
            if key.startswith(('jacket-', 'pants-', 'shirt-', 'vest-', 'monogram')):
                values = request.POST.getlist(key)
                print(f"Selected for {key}: {values}")
                
    # --- Review sorting logic starts here ---
    sort_option = request.GET.get('sort', 'most_recent')

    reviews = ReviewRating.objects.filter(product=product, status=True, parent__isnull=True)


    if sort_option == 'most_recent':
        reviews = reviews.order_by('-created_at')
    elif sort_option == 'oldest':
        reviews = reviews.order_by('created_at')
    elif sort_option == 'most_popular':
        # Change this to your actual popularity field; fallback to rating desc
        reviews = reviews.order_by('-rating', '-created_at')  # Replace 'helpful_votes' if not present
    else:
        reviews = reviews.order_by('-created_at')

    total_reviews = reviews.count()

    # --- Rating breakdown with half-star support ---
    star_steps = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

    rating_counts = reviews.values('rating').annotate(count=Count('rating'))
    ratings_breakdown = dd(int)

    for item in rating_counts:
        raw_rating = float(item['rating'])
        star = float(Decimal(str(raw_rating)).quantize(Decimal('0.5'), rounding=ROUND_HALF_UP))
        ratings_breakdown[star] += item['count']

    rating_percentages = {
        str(star): (ratings_breakdown[star] / total_reviews) * 100 if total_reviews else 0
        for star in star_steps
    }

    reply_forms = {review.id: ReviewReplyForm(prefix=str(review.id)) for review in reviews}

    context = {
        'product': product,
        'images': images,
        'first_image': product.first_image(),
        'timer': timer,
        'cart_product_form': cart_product_form,
        'set_items': set_items,
        'customizations': {k: dict(v) for k, v in customization_by_target.items()},
        'variations': variations,
        'product_pieces': product_pieces,
        'monogram_keys': monogram_keys,
        'monogram_price': monogram_price or 0,
        'vest_price': vest_price or 0,
        'shirt_price': shirt_price or 0,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'average_rating': product.average_rating,
        'ratings_breakdown': ratings_breakdown,
        'rating_percentages': rating_percentages,
        'star_steps': star_steps,
        'reply_forms': reply_forms,
        'sort_option': sort_option,  # To highlight active sort option in template
    }
    
    included_pieces = {
        'is_jacket_product': product.pieces.filter(name__iexact="jacket").exists(),
        'is_vest_product': product.pieces.filter(name__iexact="vest").exists(),
        'is_pants_product': product.pieces.filter(name__iexact="pants").exists(),
        'is_shirt_product': product.pieces.filter(name__iexact="shirt").exists(),
    }
    context.update(included_pieces)
    
    
    
    # --  AJAX fragment response  ------------------------------------------
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        html = render_to_string(
            "store/partials/review_list.html",        # fragment template
            {
                "reviews": reviews,
                "reply_forms": reply_forms,
                "sort_option": sort_option,
                # add anything else the partial needs
            },
            request=request,
        )
        return JsonResponse({"html": html})
    # ----------------------------------------------------------------------

    
    
    
    
    

    return render(request, 'store/product_detail.html', context)









def get_client_ip(request):
    """Returns the client IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip





@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    def redirect_to_product():
        return redirect(
            'store:product_detail',
            main_slug=product.sub_category.category.main_category.slug,
            category_slug=product.sub_category.category.slug,
            subcategory_slug=product.sub_category.slug,
            product_slug=product.slug
        )

    if request.method == 'POST':
        form = ReviewRatingForm(request.POST)
        if form.is_valid():
            rating = form.cleaned_data['rating']
            subject = form.cleaned_data['subject']
            review_text = form.cleaned_data['review']

            review, created = ReviewRating.objects.get_or_create(
                product=product,
                user=request.user,
                defaults={
                    'subject': subject,
                    'review': review_text,
                    'rating': rating,
                    'ip': get_client_ip(request)
                }
            )

            if not created:
                review.subject = subject
                review.review = review_text
                review.rating = rating
                review.ip = get_client_ip(request)
                review.save()
                messages.success(request, "Your review has been updated.")
            else:
                messages.success(request, "Thank you! Your review has been submitted.")
        else:
            messages.error(request, "There was an error with your review. Please try again.")
    return redirect_to_product()




@login_required
def submit_reply(request, review_id):
    parent_review = get_object_or_404(ReviewRating, id=review_id)
    product = parent_review.product

    def redirect_to_product():
        return redirect(
            'store:product_detail',
            main_slug=product.sub_category.category.main_category.slug,
            category_slug=product.sub_category.category.slug,
            subcategory_slug=product.sub_category.slug,
            product_slug=product.slug
        )

    if request.method == 'POST':
        form = ReviewReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.user = request.user
            reply.review = parent_review
            reply.save()
            messages.success(request, "Your reply has been submitted.")
            return redirect_to_product()
        else:
            messages.error(request, "There was an error submitting your reply.")
            print(form.errors)  # For debugging

    return redirect_to_product()




