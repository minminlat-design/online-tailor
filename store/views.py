from django.shortcuts import get_object_or_404, redirect, render
from cart.forms import CartAddProductForm
from category.models import MainCategory, Category, SubCategory
from store.forms import ReviewRatingForm, ReviewReplyForm
from store.models import Product, ProductImage, ReviewRating, Brand, Color
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
from django.views.decorators.http import require_POST
from content.models import StaticPage
import redis
from django.conf import settings
from django.db.models import F



import logging
logger = logging.getLogger(__name__)



# Re-use a single Redis connection for the whole module
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,     # return Python str instead of bytes
    socket_timeout=5,          # fail fast if Redis is down
)







def store(
    request,
    main_slug: str | None = None,
    category_slug: str | None = None,
    subcategory_slug: str | None = None,
    brand_slug: str | None = None,      # ← comes from /shop/brand/<slug>/
    color_slug: str | None = None,      # ← comes from /shop/color/<slug>/
):
    """
    Product catalogue with optional filters:
      • main category / category / sub-category (via path)
      • brand  (via /shop/brand/<slug>/   or legacy ?brand=<id>)
      • color  (via /shop/color/<slug>/   or legacy ?color=<id>)
    """

    # ------------------------------------------------------------------
    # Base queryset
    # ------------------------------------------------------------------
    products = Product.objects.filter(is_available=True)

    # ------------------------------------------------------------------
    # Brand filter (slug first, fall back to ?brand=id for backward compat)
    # ------------------------------------------------------------------
    selected_brand = None
    if brand_slug:
        selected_brand = get_object_or_404(Brand, slug=brand_slug)
        products = products.filter(brand=selected_brand)
    else:  # legacy query-string
        brand_id = request.GET.get("brand")
        if brand_id and brand_id.isdigit():
            selected_brand = get_object_or_404(Brand, id=int(brand_id))
            products = products.filter(brand_id=selected_brand.id)

    # ------------------------------------------------------------------
    # Color filter (slug first, fall back to ?color=id)
    # ------------------------------------------------------------------
    selected_color = None
    if color_slug:
        selected_color = get_object_or_404(Color, slug=color_slug)
        products = products.filter(color=selected_color)
    else:  # legacy query-string
        color_id = request.GET.get("color")
        if color_id and color_id.isdigit():
            selected_color = get_object_or_404(Color, id=int(color_id))
            products = products.filter(color_id=selected_color.id)
            
            
    # ------------------------------------------------------------------
    # Price filter (?price_min=&price_max=)  ← ADD THIS BLOCK
    # ------------------------------------------------------------------
    price_min = request.GET.get("price_min")
    price_max = request.GET.get("price_max")

    if price_min and price_min.isnumeric():
        products = products.filter(price__gte=price_min)

    if price_max and price_max.isnumeric():
        products = products.filter(price__lte=price_max)


    # ------------------------------------------------------------------
    # Category / sub-category filters (unchanged from your original logic)
    # ------------------------------------------------------------------
    main_category = category = sub_category = None
    subcategories = categories = None
    active_main_category_id = None

    if main_slug and category_slug and subcategory_slug:
        sub_category = get_object_or_404(
            SubCategory,
            slug=subcategory_slug,
            category__slug=category_slug,
            category__main_category__slug=main_slug,
        )
        category = sub_category.category
        main_category = category.main_category
        active_main_category_id = main_category.id
        products = products.filter(sub_category=sub_category)
        categories = _annotate_sidebar_categories(main_category)

    elif main_slug and category_slug:
        category = get_object_or_404(Category, slug=category_slug, main_category__slug=main_slug)
        main_category = category.main_category
        active_main_category_id = main_category.id

        # Annotate subcategories with product counts
        subcategories = category.subcategories.annotate(
            product_count=Count('products', filter=Q(products__is_available=True))
        )

        # Include both products from subcategories and (optionally) directly assigned to the category
        products = products.filter(
            Q(sub_category__in=subcategories) | Q(category=category)
        )

        categories = _annotate_sidebar_categories(main_category)

    elif main_slug:
        main_category = get_object_or_404(MainCategory, slug=main_slug)
        active_main_category_id = main_category.id
        categories = _annotate_sidebar_categories(main_category)
        all_subs = SubCategory.objects.filter(category__main_category=main_category)
        products = products.filter(sub_category__in=all_subs)

    # ------------------------------------------------------------------
    # Sidebar collections (brands & colors with counts)
    # ------------------------------------------------------------------
    brands = (
        Brand.objects
             .filter(products__is_available=True)
             .annotate(product_count=Count('products', filter=Q(products__is_available=True)))
             .distinct()
    )
    colors = (
        Color.objects
             .filter(products__is_available=True)
             .annotate(product_count=Count('products', filter=Q(products__is_available=True)))
             .distinct()
    )

    # ------------------------------------------------------------------
    # Extras
    # ------------------------------------------------------------------
    sale_products = Product.is_sale.all()[:3]
    gallery = Product.objects.filter(is_available=True)[:6]

    # ------------------------------------------------------------------
    # Context
    # ------------------------------------------------------------------
    context = {
        "products": products,
        "main_category": main_category,
        "category": category,
        "sub_category": sub_category,
        "subcategories": subcategories,
        "categories": categories,
        "active_category_id": category.id if category else None,
        "active_main_category_id": active_main_category_id,

        # filter widgets
        "brands": brands,
        "colors": colors,
        "selected_brand": selected_brand,
        "selected_color": selected_color,

        # extras
        "sale_products": sale_products,
        "gallery": gallery,
        
        "price_min": price_min,
        "price_max": price_max,

    }
    return render(request, "store/store.html", context)









# -------------------------------------------------------------------
# Helper to annotate every category under a main category
# -------------------------------------------------------------------


def _annotate_sidebar_categories(main_category):
    """
    Returns the categories under `main_category`
    each with:
        - product_count (all products in all sub-categories)
        - subcategories prefetched & annotated with their own product counts
    """
    return (
        main_category.categories.prefetch_related(
            Prefetch(
                "subcategories",
                queryset=SubCategory.objects.annotate(
                    product_count=Count(
                        "products",
                        filter=Q(products__is_available=True)
                    )
                ),
            )
        )
        .annotate(
            product_count=Count(
                "subcategories__products",
                filter=Q(subcategories__products__is_available=True),
                distinct=True,
            )
        )
    )






def product_detail(request, main_slug, category_slug, subcategory_slug, product_slug):

    
    
    
    product = get_object_or_404(
        Product,
        slug=product_slug,
        sub_category__slug=subcategory_slug,
        sub_category__category__slug=category_slug,
        sub_category__category__main_category__slug=main_slug
    )
    
    # Atomically increment and get the view count
    should_count = (
        request.method == "GET"
        and request.headers.get("X-Requested-With") != "XMLHttpRequest"
        and not request.GET.get("partial")
        and not request.headers.get("Purpose") == "prefetch"  # Chrome prefetch
        and not request.headers.get("Sec-Fetch-Mode") == "navigate"
        and not request.headers.get("Sec-Fetch-Site") == "none"
    )

    if should_count and not request.session.get(f"viewed_product_{product.id}"):
        total_views = r.incr(f"product:{product.id}:views")
        request.session[f"viewed_product_{product.id}"] = True

        if product.images.exists():
            main_image_id = product.images.first().id
            r.zincrby('product_view_ranking', 1, str(main_image_id))
    else:
        total_views = r.get(f"product:{product.id}:views") or 0


        
   
    
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
    
    
    # Fetch privacy policy page
    try:
        shipping_policy = StaticPage.objects.get(slug='shipping-delivery', published=True)
    except StaticPage.DoesNotExist:
        shipping_policy = None
        
        
    try:
        return_policy = StaticPage.objects.get(slug='delivery-return', published=True)
    except StaticPage.DoesNotExist:
        return_policy = None
        
        
    share_url = request.build_absolute_uri(product.get_absolute_url())



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
        'shipping_policy': shipping_policy,  # pass privacy policy as 'shipping policy'
        'return_policy': return_policy,  # pass return policy as 'return policy'
        'is_customizable': product.is_customizable, 
        'share_url': share_url,
        'total_views': total_views,
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






# ───────────────────── helper: client IP ────────────────────────────
def get_client_ip(request):
    """Return the client’s IP address."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0] if xff else request.META.get("REMOTE_ADDR")


# ───────────────────── helper: sorting  ─────────────────────────────
ORDER_MAP = {
    "most_recent":   ("-created_at",),
    "oldest":        ("created_at",),
    "most_popular":  ("-rating", "-created_at"),
}
DEFAULT_SORT = "most_recent"


def get_sorted_reviews(product, sort_key):
    """Return top-level reviews (no parents) in requested order."""
    ordering = ORDER_MAP.get(sort_key, ORDER_MAP[DEFAULT_SORT])
    return (
        ReviewRating.objects
        .filter(product=product, status=True, parent=None)
        .order_by(*ordering)
        .select_related("user")
        .prefetch_related("replies")  # assumes related_name="replies"
    )


# ───────────────────── view: submit_review  ─────────────────────────
@login_required                    # remove if you allow guest reviews
@require_POST
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form    = ReviewRatingForm(request.POST)

    def _redirect():
        return redirect(
            "store:product_detail",
            main_slug        = product.sub_category.category.main_category.slug,
            category_slug    = product.sub_category.category.slug,
            subcategory_slug = product.sub_category.slug,
            product_slug     = product.slug,
        )

    # ---------- validation error ------------------------------------
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        messages.error(request, "There was an error with your review.")
        return _redirect()

    # ---------- create / update ------------------------------------
    cd = form.cleaned_data
    review, created = ReviewRating.objects.get_or_create(
        product  = product,
        user     = request.user,
        defaults = {
            "subject": cd["subject"],
            "review" : cd["review"],
            "rating" : cd["rating"],
            "ip"     : get_client_ip(request),
        },
    )
    if not created:                        # user edited existing review
        review.subject = cd["subject"]
        review.review  = cd["review"]
        review.rating  = cd["rating"]
        review.ip      = get_client_ip(request)
        review.save()

    msg = "Thank you! Your review has been submitted." if created \
          else "Your review has been updated."

    # ---------- AJAX branch ----------------------------------------
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        sort_opt   = request.GET.get("sort", DEFAULT_SORT)
        reviews_qs = get_sorted_reviews(product, sort_opt)

        reviews_html = render_to_string(
            "store/partials/review_list.html",
            {
                "product":     product,
                "reviews":     reviews_qs,
                "sort_option": sort_opt,
            },
            request=request,
        )
        return JsonResponse(
            {"message": msg, "reviews_html": reviews_html},
            status=201 if created else 200,
        )

    # ---------- non-AJAX fallback ----------------------------------
    messages.success(request, msg)
    return _redirect()




# ───────────────────── view: submit_reply  ─────────────────────────
@login_required
@require_POST
def submit_reply(request, review_id):
    parent_review = get_object_or_404(ReviewRating, id=review_id)
    product       = parent_review.product

    def _redirect():
        return redirect(
            "store:product_detail",
            main_slug        = product.sub_category.category.main_category.slug,
            category_slug    = product.sub_category.category.slug,
            subcategory_slug = product.sub_category.slug,
            product_slug     = product.slug,
        )

    form = ReviewReplyForm(request.POST)
    if not form.is_valid():
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"errors": form.errors}, status=400)
        messages.error(request, "There was an error submitting your reply.")
        return _redirect()

    # ---------- save reply -----------------------------------------
    reply = form.save(commit=False)
    reply.user   = request.user
    reply.review = parent_review
    reply.ip     = get_client_ip(request)
    reply.save()

    msg = "Your reply has been submitted."

    # ---------- AJAX branch ----------------------------------------
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        sort_opt   = request.GET.get("sort", DEFAULT_SORT)
        reviews_qs = get_sorted_reviews(product, sort_opt)

        reviews_html = render_to_string(
            "store/partials/review_list.html",
            {
                "product":     product,
                "reviews":     reviews_qs,
                "sort_option": sort_opt,
            },
            request=request,
        )
        return JsonResponse(
            {"message": msg, "reviews_html": reviews_html},
            status=201,
        )

    # ---------- non-AJAX fallback ----------------------------------
    messages.success(request, msg)
    return _redirect()








import logging
logger = logging.getLogger(__name__)

@login_required
def image_ranking(request):
    """
    Show the 10 images with the highest view scores,
    in the exact order Redis returns, plus debug info.
    """

    # ── 1. Pull the top 10 IDs from Redis ──────────────────────────────
    image_ids = r.zrevrange("product_view_ranking", 0, 9)  # strings
    logger.debug("Redis zrevrange returned: %s", image_ids)

    if not image_ids:
        logger.warning("Redis sorted-set 'product_view_ranking' is empty.")
        return render(
            request,
            "images/image/ranking.html",
            {"section": "images", "most_viewed": [], "debug_ids": image_ids},
        )

    # ── 2. Convert to ints for the ORM and fetch rows ──────────────────
    id_ints = [int(pk) for pk in image_ids]
    images_qs = (
        ProductImage.objects.filter(id__in=id_ints)
        .select_related("product", "color")
    )
    images = list(images_qs)
    logger.debug("DB returned IDs: %s", [img.id for img in images])

    # ── 3. Preserve Redis order (highest score first) ──────────────────
    images.sort(key=lambda img: id_ints.index(img.id))

    # ── 4. Optional: surface debug data in the template when
    #        ?debug=1 is present in the URL ─────────────────────────────
    context = {
        "section": "images",
        "most_viewed": images,
    }
    if request.GET.get("debug") == "1":
        context.update(
            redis_ids=image_ids,
            db_ids=[img.id for img in images],
            redis_dump=r.zrevrange("product_view_ranking", 0, 9, withscores=True),
        )

    return render(request, "images/image/ranking.html", context)
