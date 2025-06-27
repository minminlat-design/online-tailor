from decimal import Decimal
import re
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from measurement.forms import DynamicMeasurementForm
from measurement.models import ProductType, UserMeasurement
from store.models import Product, ProductVariation
from variation.models import VariationOption
from .cart import Cart, CartSettings
from .forms import CartAddProductForm
from datetime import datetime, timedelta
from .models import CartItem
from django.contrib.auth.decorators import login_required
from django.contrib import messages








@require_POST
def cart_add(request, product_id):
    print("Request POST data:", request.POST)

    # Track checkbox selections (True if checked)
    checkbox_flags = {
        'monogram_selected': request.POST.get('jacket_monogram_selected') == 'on',
        'shirt_selected': request.POST.get('shirt_selected') == 'on',
        'vest_selected': request.POST.get('vest_selected') == 'on',
        'shirt_monogram_selected': request.POST.get('shirt_monogram_selected') == 'on',
    }
    for key, val in checkbox_flags.items():
        print(f"{key}: {val}")

    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        print("Cleaned data:", cd)

        selected_options = {}

        # Inject base prices only if checkbox selected
        base_price_fields = {
            'monogram': 'monogram_price',
            'shirt': 'shirt_price',
            'vest': 'vest_price',
        }
        for category, price_field in base_price_fields.items():
            if checkbox_flags.get(f'{category}_selected'):
                selected_options.setdefault(category, {})
                selected_options[category]['price'] = {
                    'id': None,
                    'name': f"{category.title()} Base Price",
                    'price_difference': request.POST.get(price_field, '0.00')
                }

        # Shirt monogram price if selected
        if checkbox_flags['shirt_monogram_selected']:
            selected_options.setdefault('shirt', {})
            selected_options['shirt']['monogram_price'] = {
                'id': None,
                'name': 'Shirt Monogram Price',
                'price_difference': request.POST.get('shirt_monogram_price', '0.00')
            }

        # Categories requiring checkboxes to be selected
        categories_with_checkboxes = {
            'monogram': 'monogram_selected',
            'shirt': 'shirt_selected',
            'vest': 'vest_selected',
            'shirt_monogram': 'shirt_monogram_selected',
        }

        # Categories always allowed without checkbox
        categories_always_allowed = {'jacket', 'pants', 'set'}

        # Parse all POST keys for options and prices
        for key, values in request.POST.lists():
            if key in ['quantity', 'override', 'csrfmiddlewaretoken']:
                continue

            if '_' in key and not key.endswith('_price'):
                category, option_name = key.split('_', 1)

                if category in categories_always_allowed or checkbox_flags.get(categories_with_checkboxes.get(category, ''), False):
                    # Skip adding the base variation option if base price is already added
                    # For example, if category=='shirt' and option_name=='shirt', and base price exists, skip
                    if category == 'shirt' and option_name == 'shirt' and checkbox_flags.get('shirt_selected'):
                        # base price already added, skip this variation option
                        continue
                    
                    # When parsing vest options, skip adding the vest option price if base vest checkbox is selected
                    if category == 'vest' and option_name == 'vest' and checkbox_flags.get('vest_selected'):
                        # If you want to avoid double counting, skip this variation option
                        continue


                    selected_options.setdefault(category, {})
                    for val in values:
                        try:
                            option = VariationOption.objects.get(id=int(val))
                            selected_options[category][option_name] = {
                                'id': option.id,
                                'name': option.name,
                                'price_difference': '0.00'  # default, updated below
                            }
                        except (VariationOption.DoesNotExist, ValueError):
                            pass


            # Parse price fields (e.g. vest_vest_31_price: 50.00)
            elif key.endswith('_price'):
                price_val = values[0] if values else '0.00'

                match = re.match(r'^([a-z]+)_(.+?)_(\d+)_price$', key.lower())
                if not match:
                    continue

                category_prefix, option_name_slug, option_id_str = match.groups()
                option_id = int(option_id_str)

                # Check if this category is allowed
                checkbox_key = categories_with_checkboxes.get(category_prefix)
                allowed = (category_prefix in categories_always_allowed) or (checkbox_key and checkbox_flags.get(checkbox_key))
                if not allowed:
                    # Skip prices for categories not selected
                    continue

                # Find matching option inside selected_options to update price_difference
                for cat_opt, options in selected_options.items():
                    for opt_key, opt_data in options.items():
                        opt_key_slug = opt_key.replace(" ", "-").lower()
                        full_key = f"{cat_opt}_{opt_key_slug}_price"
                        if key.lower() == full_key or opt_data.get('id') == option_id:
                            opt_data['price_difference'] = price_val
                            print(f"Matched price: {key} → {cat_opt}_{opt_key} → {price_val}")

        print("Final selected_options dict:", selected_options)

        # Customization free text fields
        customizations = {}
        if jacket_text := request.POST.get("jacket_monogram_text", "").strip():
            customizations["jacket_monogram_text"] = jacket_text
        if shirt_text := request.POST.get("shirt_monogram_text", "").strip():
            customizations["shirt_monogram_text"] = shirt_text

        print("Final customizations dict:", customizations)
        
        # 🕒 Compute estimated delivery date
        delivery_days = product.delivery_days or 7  # Default fallback
        delivery_date = (datetime.today() + timedelta(days=delivery_days)).strftime("%b %d, %Y")


        # Add to cart
        cart.add(
            product=product,
            quantity=cd['quantity'],
            override_quantity=cd['override'],
            selected_options=selected_options,
            customizations=customizations,
            delivery_date=delivery_date,
        )

        # AJAX response
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            extra_price = Decimal('0.00')
            for category, options in selected_options.items():
                for option in options.values():
                    try:
                        extra_price += Decimal(option.get('price_difference', '0'))
                    except Exception:
                        pass

            unit_price = Decimal(product.discounted_price or product.price) + extra_price
            item_total = unit_price * cd['quantity']

            return JsonResponse({
                'success': True,
                'quantity': cd['quantity'],
                'total_price': f"{cart.get_total_price():.2f}",
                'item_total': f"{item_total:.2f}",
            })

    return redirect('cart:cart_detail')




@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    cart.save()

    return JsonResponse({
        'success': True,
        'total_price': f"{cart.get_total_price():.2f}",
        'item_count': len(cart),
    })


def cart_detail(request):
    cart = Cart(request)
    free_shipping_data = cart.get_free_shipping_data()
    gift_wrap_status = cart.gift_wrap

    try:
        settings_obj = CartSettings.objects.latest('id')
    except CartSettings.DoesNotExist:
        settings_obj = CartSettings(
            free_shipping_threshold=Decimal('300.00'),
            gift_wrap_price=Decimal('5.00')
        )

    for item in cart:
        # Form to update quantity
        item['update_quantity_form'] = CartAddProductForm(
            initial={'quantity': item['quantity'], 'override': True}
        )

        
   

    return render(request, 'cart/detail.html', {
        'cart': cart,  # cart now includes delivery dates per item
        'free_shipping_data': free_shipping_data,
        'gift_wrap': gift_wrap_status,
        'gift_wrap_price': settings_obj.gift_wrap_price,
    })



@require_GET
def cart_shipping_info(request):
    cart = Cart(request)
    free_shipping_data = cart.get_free_shipping_data()

    return JsonResponse({
        'progress': free_shipping_data['progress'],
        'remaining': str(free_shipping_data['remaining']),
        'qualified': free_shipping_data['qualified'],
    })


@require_POST
def cart_update_quantity(request):
    cart = Cart(request)

    try:
        data = json.loads(request.body)
        cart_key = data.get('cart_key')
        quantity = int(data.get('quantity', 1))

        if quantity < 1:
            quantity = 1

        # ✅ Extract selected_options and customizations from session cart
        cart_item = cart.cart.get(cart_key)
        if not cart_item:
            return JsonResponse({"success": False, "error": "Item not found in cart"})

        selected_options = cart_item.get('selected_options', {})
        customizations = cart_item.get('customizations', {})

        # ✅ Get product by cart_key
        product = cart.get_product_by_key(cart_key)
        if not product:
            return JsonResponse({"success": False, "error": "Invalid product"})

        # ✅ Update cart
        cart.update(product, quantity, selected_options, customizations)
        cart.save()

        item_total = cart.get_item_total(product, selected_options, customizations)
        total_price = cart.get_total_price()

        return JsonResponse({
            "success": True,
            "item_total": f"{item_total:.2f}",
            "total_price": f"{total_price:.2f}",
            "quantity": quantity,
            "item_count": len(cart),
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@require_POST
def toggle_gift_wrap(request):
    data = json.loads(request.body)
    enable = data.get('enable', False)

    cart = Cart(request)
    cart.toggle_gift_wrap(enable)

    return JsonResponse({
        'success': True,
        'gift_wrap': cart.gift_wrap,
        'total_price': str(cart.get_total_price()),
    })
    
    
    
# move session to the cart
@login_required
def cart_to_checkout(request):
    print("[DEBUG] Entered cart_to_checkout view")

    cart = Cart(request)
    session_cart = request.session.get('cart', {})

    print("[DEBUG] Raw session cart data:", session_cart)

    # ✅ Step 1: Clear old CartItems for this user
    CartItem.objects.filter(user=request.user).delete()
    print("[DEBUG] Cleared existing CartItems for user")
    
    # Copy items from session

    count = 0
    for key, item in session_cart.items():
        try:
            product_id = int(key.split(":")[0])
        except (ValueError, IndexError):
            print(f"[WARN] Invalid cart key format: {key}")
            continue

        product = get_object_or_404(Product, id=product_id)
        selected_options = item.get('selected_options', {})
        customizations = item.get('customizations', {})
        quantity = item.get('quantity', 1)
        base_price = product.discounted_price or product.price

        print(f"[DEBUG] Creating new CartItem for {product.name}")
        CartItem.objects.create(
            user=request.user,
            product=product,
            quantity=quantity,
            base_price=base_price,
            selected_options=selected_options,
            customizations=customizations,
            gift_wrap=cart.gift_wrap,
        )
        count += 1
        
    # Check if any custom items still lack measurement
    missing_measurement = CartItem.objects.filter(
        user=request.user,
        product__is_customizable=True,
        user_measurement__isnull=True,
    )
    print("[DEBUG] still missing:", missing_measurement.count())
    
    if missing_measurement.exists():
        # Need to collect body measurements
        return redirect('cart:measurement_form_view')
    
    # All good - proceed to shipping / payment

    # (Optional) Clear session cart to avoid resync confusion
    # cart.clear()

    print(f"[DEBUG] Finished copying. Total items created: {count}")
    messages.success(request, f"{count} item(s) moved to your checkout.")
    return redirect('orders:shipping_info')





def determine_product_type(cart_items):
    # Define your priority order
    priority = ["shirt", "jacket", "coat", "vest", "pants", "shorts"]
    product_types = [item.product.product_type.slug for item in cart_items if item.product.product_type]

    for p_type in priority:
        if p_type in product_types:
            return ProductType.objects.get(slug=p_type)

    return None





def get_measurement_keys_for_product(product_type):
    """
    Given a ProductType instance, returns a list of measurement keys (slug field) 
    required for that product type.
    """
    if not product_type:
        return []

    return list(
        product_type.measurements.select_related("measurement_type")
        .values_list("measurement_type__key", flat=True)
    )



@login_required
def measurement_form_view(request):
    # Get ALL cart items for this user (used for summary)
    all_cart_items = CartItem.objects.filter(user=request.user)
    
    # Get ONLY items that need measurement (used for forms)
    cart_items_needing_measurement = all_cart_items.filter(user_measurement__isnull=True, product__is_customizable=True)

    # If no measurement needed, redirect to checkout
    if not cart_items_needing_measurement.exists():
        return redirect('cart:cart_to_checkout')

    print(f"[DEBUG] Found {cart_items_needing_measurement.count()} cart items needing measurement.")
    for item in cart_items_needing_measurement:
        print(f"[DEBUG] → {item.product.name} | quantity: {item.quantity}")

    existing_profiles = UserMeasurement.objects.filter(user=request.user)
    item_forms = []

    if request.method == "POST":
        if "use_existing" in request.POST:
            profile_id = request.POST.get("existing_profile_id")
            selected_profile = get_object_or_404(existing_profiles, id=profile_id)
            cart_items_needing_measurement.update(user_measurement=selected_profile)
            messages.success(request, "Saved measurement profile applied successfully.")
            return redirect('orders:shipping_info')


        all_valid = True
        item_forms = []

        for item in cart_items_needing_measurement:
            product_type = item.product.product_type
            measurement_keys = get_measurement_keys_for_product(product_type)
            form = DynamicMeasurementForm(
                request.POST,
                request.FILES,
                prefix=f"item_{item.id}",
                measurement_keys=measurement_keys
            )

            item_forms.append((item, form))  # Add form regardless of validity

            if not form.is_valid():
                all_valid = False
                continue  # Skip this item

            measurement = form.save(user=request.user)

            item.user_measurement = measurement
            item.frozen_measurement_data = {
                "fit_type": measurement.fit_type,
                "data": measurement.measurement_data,
                "photos": {
                    "front": measurement.photo_front.url if measurement.photo_front else None,
                    "side": measurement.photo_side.url if measurement.photo_side else None,
                    "back": measurement.photo_back.url if measurement.photo_back else None,
                }
            }
            item.save()
        print(f"[DEBUG] Saved frozen data for item {item.id}: {item.frozen_measurement_data}")


        if all_valid:
            messages.success(request, "Measurements submitted successfully.")
            return redirect('orders:shipping_info')
        else:
            messages.error(request, "There was an error in the form. Please correct the highlighted fields.")


    else:
        for item in cart_items_needing_measurement:
            product_type = item.product.product_type
            measurement_keys = get_measurement_keys_for_product(product_type)
            form = DynamicMeasurementForm(prefix=f"item_{item.id}", measurement_keys=measurement_keys)
            item_forms.append((item, form))
            
            
    for item, form in item_forms:
       print(f"DEBUG ITEM ID: {item.id} | Product: {item.product.name}")


    # Calculate extra options with prices for each cart item
    extra_options_per_item = {}

    for item, form in item_forms:
        item_key = item.pk or item.product.pk
        extras = []
        selected_options = item.selected_options or {}

        for key, val in selected_options.items():
            # Skip if val is not a dict
            if not isinstance(val, dict):
                continue

            # Case 1: Direct option with price_difference
            price_diff = val.get("price_difference")
            if price_diff and Decimal(price_diff) > 0:
                extras.append({
                    "label": key,
                    "name": val.get("name") or (val.get("items") or {}).get("name"),
                    "price": Decimal(price_diff)
                })

            # Case 2: Nested sub-options
            elif "items" in val and isinstance(val["items"], dict):
                for subkey, subval in val["items"].items():
                    if isinstance(subval, dict):
                        sub_price = subval.get("price_difference")
                        if sub_price and Decimal(sub_price) > 0:
                            extras.append({
                                "label": f"{key} - {subkey}",
                                "name": subval.get("name"),
                                "price": Decimal(sub_price)
                            })

        extra_options_per_item[item_key] = extras


    # Annotate ALL cart items with unit_price for display
    for item in all_cart_items:
        try:
            item.unit_price = item.total_price / item.quantity
        except (ZeroDivisionError, TypeError):
            item.unit_price = item.base_price

    subtotal = sum(item.total_price for item in all_cart_items)

    return render(request, "cart/measurement_form.html", {
        "item_forms": item_forms,
        "existing_profiles": existing_profiles,
        "cart_items": all_cart_items,  # full cart for summary
        "subtotal": subtotal,
        "extra_options_per_item": extra_options_per_item,
    })
