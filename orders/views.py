from django.db import transaction
from decimal import Decimal, ROUND_HALF_UP
from cart.cart import Cart 
from django.urls import reverse
from cart.models import CartItem
from fashion_01 import settings
from orders.models import Order, OrderItem
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import ShippingForm
from django.shortcuts import render, redirect
import stripe
from orders.tasks import order_created
import json
import weasyprint
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from pprint import pprint
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
import logging
from cart.models import CartSettings
from store.models import ShippingFee  
from coupons.models import Coupon
from cart.cart import get_cart_settings
 
logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_order_from_cart(
    user,
    shipping_data: dict,
    *,
    shipping_fee: Decimal = Decimal("0.00"),
    gift_wrap_fee: Decimal = None,   # total fee; None → compute per‑item
    discount: Decimal = Decimal("0.00"),
    coupon=None
) -> Order:
    cart_items = CartItem.objects.filter(user=user, is_active=True)
    if not cart_items.exists():
        raise ValueError("Cart is empty")

    # Fallback per‑item gift‑wrap computation
    if gift_wrap_fee is None:
        try:
            per_item_wrap_price = CartSettings.objects.latest("id").gift_wrap_price
        except CartSettings.DoesNotExist:
            per_item_wrap_price = Decimal("5.00")

        gift_wrap_fee = sum(
            per_item_wrap_price * ci.quantity
            for ci in cart_items
            if ci.gift_wrap
        )
        print(f"[DEBUG] Computed gift_wrap_fee: {gift_wrap_fee}")

    with transaction.atomic():

        # 1️⃣ Create the shell order
        order = Order.objects.create(
            user          = user,
            first_name    = shipping_data["first_name"],
            last_name     = shipping_data["last_name"],
            email         = shipping_data["email"],
            address       = shipping_data["address"],
            postal_code   = shipping_data["postal_code"],
            city          = shipping_data["city"],
            phone         = shipping_data.get("phone", ""),
            country       = shipping_data.get("country", ""),
            paid          = False,
            status        = "pending",
            shipping_fee  = shipping_fee,
            gift_wrap_fee = gift_wrap_fee,
            discount      = discount,
            total_price   = Decimal("0.00"),   # temp; fixed below
        )
        print(f"[DEBUG] Created order id={order.id}")

        # 2️⃣ Copy line items & freeze measurements
        items_total = Decimal("0.00")

        for ci in cart_items:
            print(f"[DEBUG] CartItem: product={ci.product.name}, quantity={ci.quantity}, "
                  f"base_price={ci.base_price}, total_price={ci.total_price}, gift_wrap={ci.gift_wrap}")

            OrderItem.objects.create(
                order                    = order,
                product                  = ci.product,
                product_name             = ci.product.name,
                quantity                 = ci.quantity,
                base_price               = ci.base_price,
                total_price              = ci.total_price,
                gift_wrap                = ci.gift_wrap,
                frozen_measurement_data  = ci.frozen_measurement_data or {},
                selected_options         = ci.selected_options,
                customizations           = ci.customizations,
                user_measurement         = ci.user_measurement,
            )
            items_total += ci.total_price
            ci.is_active = False        # remove from cart
            ci.save()

        print(f"[DEBUG] Items total price sum: {items_total}")
        print(f"[DEBUG] Gift wrap fee: {gift_wrap_fee}")
        print(f"[DEBUG] Shipping fee: {shipping_fee}")
        print(f"[DEBUG] Discount: {discount}")

        # 3️⃣ Finalise money fields
        order.total_price = (
            items_total
            + gift_wrap_fee
            + shipping_fee
            - discount
        )
        order.save()
        print(f"[DEBUG] Final order total_price: {order.total_price}")

    return order





@login_required
def shipping_info_view(request):
    cart = Cart(request)

    cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart:cart_detail')

    # Use cart.get_total_price() which sums session cart items and gift wrap once
    subtotal = cart.get_total_price()
    total_with_gift_wrap = subtotal  # gift wrap included already

    # Coupon
    coupon = None
    discount_amount = Decimal("0.00")
    total_after_discount = total_with_gift_wrap

    coupon_id = request.session.get("coupon_id")
    if coupon_id:
        try:
            coupon = Coupon.objects.get(id=coupon_id, active=True)
            discount_amount = (coupon.discount / Decimal("100")) * total_with_gift_wrap
            total_after_discount = total_with_gift_wrap - discount_amount
        except Coupon.DoesNotExist:
            pass

    # Handle POST form ...
    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            request.session['shipping_info'] = {
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'email': data['email'],
                'address': data['address'],
                'postal_code': data['postal_code'],
                'city': data['city'],
                'phone': data['phone'],
                'country': data['country'],
            }
            print("[DEBUG] Shipping info saved:", request.session['shipping_info'])
            return redirect('orders:review_order')
    else:
        form = ShippingForm(initial=request.session.get('shipping_info'))

    return render(request, 'orders/shipping_info.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'gift_wrap': cart.gift_wrap,
        'gift_wrap_price': cart.gift_wrap_price if cart.gift_wrap else Decimal("0.00"),
        'coupon': coupon,
        'discount_amount': discount_amount,
        'total_after_discount': total_after_discount,
    })





    """
    
    # coupon discount working on stripe page
   


@login_required
def review_order_view(request):
    # ── 1. Sanity checks ───────────────────────────────────────────
    shipping_info = request.session.get("shipping_info")
    if not shipping_info:
        messages.error(request, "Shipping information is missing.")
        return redirect("orders:shipping_info")

    cart       = Cart(request)
    cart_items = list(cart)
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # ── 2. Money figures (unchanged from your version) ─────────────
    original_subtotal        = cart.get_total_price()           # before coupon
    discount_amount          = cart.get_discount()              # already $‑value
    subtotal_after_discount  = cart.get_total_price_after_discount()
    gift_wrap_fee            = cart.gift_wrap_price if cart.gift_wrap else Decimal("0.00")
    shipping_fee             = cart.get_shipping_fee()
    grand_total              = cart.get_grand_total()           # after all fees
    coupon                   = cart.coupon                      # Coupon instance | None

    # ── 3. POST → create Order → Stripe session ───────────────────
    if request.method == "POST":
        # 3‑A  create the Order in DB
        order = create_order_from_cart(
            user           = request.user,
            shipping_data  = shipping_info,
            shipping_fee   = shipping_fee,
            gift_wrap_fee  = gift_wrap_fee,
            discount       = discount_amount,
            coupon         = coupon,
        )
        order_created.delay(order.id)

        # 3‑B  build Stripe line‑items
        line_items = []
        for oi in order.items.all():
            cents = int((oi.total_price / oi.quantity) * 100)
            line_items.append({
                "price_data": {
                    "currency"    : "usd",
                    "unit_amount" : cents,
                    "product_data": {"name": oi.product_name},
                },
                "quantity": oi.quantity,
            })

        if order.gift_wrap_fee > 0:
            line_items.append({
                "price_data": {
                    "currency"    : "usd",
                    "unit_amount" : int(order.gift_wrap_fee * 100),
                    "product_data": {"name": "Gift‑wrap fee"},
                },
                "quantity": 1,
            })

        if order.shipping_fee > 0:
            line_items.append({
                "price_data": {
                    "currency"    : "usd",
                    "unit_amount" : int(order.shipping_fee * 100),
                    "product_data": {"name": "Shipping fee"},
                },
                "quantity": 1,
            })

        # 3‑C  create/re‑use a Stripe coupon so the discount
        #      is VISIBLE to the customer in Checkout
        discounts_array = []     # ← value we’ll feed to Session.create()

        if coupon and discount_amount > 0:
            stripe_coupon_id = getattr(coupon, "stripe_id", None)

            # create on‑the‑fly if we haven’t stored one before
            if not stripe_coupon_id:
                # You may have discount_type ("percent" / "amount");
                # fallback to % if field not present.
                if getattr(coupon, "discount_type", "percent") == "percent":
                    stripe_coupon = stripe.Coupon.create(
                        name        = coupon.code,
                        percent_off = float(coupon.discount),   # 10 → 10 %
                        duration    = "once",
                    )
                else:  # fixed $ amount
                    stripe_coupon = stripe.Coupon.create(
                        name        = coupon.code,
                        amount_off  = int(coupon.discount * 100),  # dollars → cents
                        currency    = "usd",
                        duration    = "once",
                    )
                coupon.stripe_id = stripe_coupon.id
                coupon.save(update_fields=["stripe_id"])
                stripe_coupon_id = stripe_coupon.id

            discounts_array = [{"coupon": stripe_coupon_id}]

        # 3‑D  create the Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types = ["card"],
            mode                 = "payment",
            line_items           = line_items,
            discounts            = discounts_array,
            metadata             = {"order_id": order.id},
            client_reference_id  = str(order.id),
            success_url = request.build_absolute_uri(
                reverse("orders:payment_success")
            ),
            cancel_url  = request.build_absolute_uri(
                reverse("orders:payment_cancel")
            ),
        )
        return redirect(session.url, code=303)

    # ── 4. GET → render page ───────────────────────────────────────
    return render(
        request,
        "orders/review_order.html",
        {
            "shipping_info"           : shipping_info,
            "cart_items"              : cart_items,
            # Template expects subtotal already discounted:
            "subtotal"                : subtotal_after_discount,
            "discount"                : discount_amount,
            "subtotal_after_discount" : subtotal_after_discount,
            "gift_wrap_price"         : gift_wrap_fee,
            "shipping_fee"            : shipping_fee,
            "grand_total"             : grand_total,
            "original_subtotal"       : original_subtotal,
        },
    )

 """
 
 
@login_required
def review_order_view(request):
    # ───────────────────────── 1. Sanity checks ────────────────────────────
    shipping_info = request.session.get("shipping_info")
    if not shipping_info:
        messages.error(request, "Shipping information is missing.")
        return redirect("orders:shipping_info")

    cart        = Cart(request)          # session cart
    cart_items  = list(cart)
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    # ───────────────────────── 2. Monetary figures ─────────────────────────
    gift_wrap_enabled = cart.gift_wrap
    gift_wrap_fee     = cart.gift_wrap_price

    subtotal               = cart.get_total_price()            # includes gift‑wrap
    original_subtotal      = subtotal
    discount_amount        = cart.get_discount()
    subtotal_after_discount= cart.get_total_price_after_discount()
    shipping_fee           = cart.get_shipping_fee()
    grand_total            = cart.get_grand_total()             # includes wrap & ship
    applied_coupon         = cart.coupon

    # DEBUG: Print cart summary info
    print("=== CART SUMMARY ===")
    print(f"Subtotal: {subtotal}")
    print(f"Gift wrap enabled: {gift_wrap_enabled}, fee: {gift_wrap_fee}")
    print(f"Shipping fee: {shipping_fee}")
    print(f"Discount amount: {discount_amount}")
    print(f"Grand total: {grand_total}")
    print(f"Coupon applied: {applied_coupon}")

    if request.method == "POST":
        # 3‑A  Create order in DB
        order = create_order_from_cart(
            user          = request.user,
            shipping_data = shipping_info,
            shipping_fee  = shipping_fee,
            gift_wrap_fee = gift_wrap_fee,
            discount      = discount_amount,
            coupon        = applied_coupon,
        )

        # DEBUG: Print order items after creation
        print("=== ORDER ITEMS AFTER CREATION ===")
        for oi in order.items.all():
            print(f"Product: {oi.product_name}, Quantity: {oi.quantity}, Total Price: {oi.total_price}")

        order_created.delay(order.id)

        # 3‑B  Build Stripe line‑items
        items_total_before_fee = sum(oi.total_price for oi in order.items.all())
        print(f"Items total before fees (sum of order items): {items_total_before_fee}")

        line_items = []

        for oi in order.items.all():
            proportion = (oi.total_price / items_total_before_fee) if items_total_before_fee else Decimal("0")
            item_discount = (discount_amount * proportion).quantize(Decimal("0.01"), ROUND_HALF_UP)
            discounted_total = (oi.total_price - item_discount).quantize(Decimal("0.01"))
            unit_price = (discounted_total / oi.quantity).quantize(Decimal("0.01"), ROUND_HALF_UP)

            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(unit_price * 100),  # cents
                    "product_data": {"name": oi.product_name},
                },
                "quantity": oi.quantity,
            })

        # Check gift wrap presence in order items
        gift_wrap_in_order_items = any(
            oi.product_name.lower() in ["gift-wrap fee", "gift‑wrap fee"]
            for oi in order.items.all()
        )
        print(f"Gift wrap included in order items? {gift_wrap_in_order_items}")

        if gift_wrap_enabled and gift_wrap_fee > 0 and not gift_wrap_in_order_items:
            print(f"Adding gift wrap fee to Stripe line items: {gift_wrap_fee}")
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(gift_wrap_fee * 100),
                    "product_data": {"name": "Gift‑wrap fee"},
                },
                "quantity": 1,
            })

        if shipping_fee > 0:
            print(f"Adding shipping fee to Stripe line items: {shipping_fee}")
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(shipping_fee * 100),
                    "product_data": {"name": "Shipping fee"},
                },
                "quantity": 1,
            })

        if applied_coupon and discount_amount > 0:
            print(f"Adding coupon to Stripe line items: {applied_coupon.code} discount {discount_amount}")
            line_items.append({
                "price_data": {
                    "currency": "usd",
                    "unit_amount": 0,
                    "product_data": {
                        "name": f"Coupon {applied_coupon.code} – ‑${discount_amount}",
                    },
                },
                "quantity": 1,
            })

        # DEBUG: Print final Stripe line items
        print("=== FINAL STRIPE LINE ITEMS ===")
        for li in line_items:
            pname = li['price_data']['product_data']['name']
            amount = li['price_data']['unit_amount'] / 100
            qty = li['quantity']
            print(f"{pname}: ${amount:.2f} x {qty}")

        # 3‑C  Stripe Checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=line_items,
            metadata={"order_id": order.id},
            client_reference_id=str(order.id),
            success_url=request.build_absolute_uri(reverse("orders:payment_success")),
            cancel_url=request.build_absolute_uri(reverse("orders:payment_cancel")),
        )
        return redirect(session.url, code=303)

    # ───────────────────────── 4. GET → render page ────────────────────────
    return render(
        request,
        "orders/review_order.html",
        {
            "shipping_info"          : shipping_info,
            "cart_items"             : cart_items,
            "subtotal"               : subtotal_after_discount,
            "gift_wrap_fee"          : gift_wrap_fee,
            "shipping_fee"           : shipping_fee,
            "discount"               : discount_amount,
            "grand_total"            : grand_total,
            "original_subtotal"      : original_subtotal,
            "subtotal_after_discount": subtotal_after_discount,
        },
    )



 
 
@login_required
def payment_success_view(request):
    # Clear session-based cart
    cart = Cart(request)
    cart.clear()

    # Clear DB-based cart items
    CartItem.objects.filter(user=request.user, is_active=True).delete()

    # Clear session shipping info if present
    request.session.pop('shipping_info', None)

    messages.success(request, "Payment successful! Thank you for your order.")
    return render(request, 'orders/payment_success.html')




@login_required
def payment_cancel_view(request):
    messages.warning(request, "Payment was canceled.")
    return render(request, 'orders/payment_cancel.html')








@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    for item in order.items.all():
        # Ensure selected_options is a dict
        if isinstance(item.selected_options, str):
            try:
                item.selected_options = json.loads(item.selected_options)
            except json.JSONDecodeError:
                item.selected_options = {}
        elif item.selected_options is None:
            item.selected_options = {}

        # 🐞 Debug log to console
        print("\n=====================")
        print(f"Item: {item.product.name}")
        print("Parsed selected_options:")
        pprint(item.selected_options)  # This prints nested structure
        print("=====================\n")

        # Ensure frozen_measurement_data is a dict
        if isinstance(item.frozen_measurement_data, str):
            try:
                item.frozen_measurement_data = json.loads(item.frozen_measurement_data)
            except json.JSONDecodeError:
                item.frozen_measurement_data = {}
        elif item.frozen_measurement_data is None:
            item.frozen_measurement_data = {}

        # Photos for preview
        measurement = getattr(item, 'user_measurement', None)
        item.photos = {
            'front': measurement.photo_front.url if measurement and measurement.photo_front else None,
            'side': measurement.photo_side.url if measurement and measurement.photo_side else None,
            'back': measurement.photo_back.url if measurement and measurement.photo_back else None,
        }

    return render(request, 'admin/orders/order/detail.html', {'order': order})








@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/pdf.html', {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    
    weasyprint.HTML(string=html).write_pdf(
        target=response,
        stylesheets=[weasyprint.CSS(finders.find('css/pdf.css'))]
    )
    return response



from weasyprint import HTML

@staff_member_required
def admin_order_invoice_pdf(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                body {{
                    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
                    font-size: 14px;
                    color: #333;
                    margin: 40px;
                    line-height: 1.6;
                }}
                h1 {{
                    font-size: 24px;
                    margin-bottom: 10px;
                    color: #1a1a1a;
                }}
                h2 {{
                    font-size: 18px;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    color: #333;
                }}
                h4 {{
                    margin: 10px 0 5px;
                    font-weight: bold;
                    color: #555;
                }}
                .order-meta {{
                    margin-bottom: 20px;
                    padding: 10px 0;
                    border-bottom: 1px solid #ddd;
                }}
                .item {{
                    margin-bottom: 30px;
                    padding: 20px;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    background-color: #f9f9f9;
                }}
                .photos {{
                    display: flex;
                    gap: 10px;
                    margin: 10px 0;
                }}
                img {{
                    max-width: 100px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    margin-bottom: 15px;
                }}
                th, td {{
                    border: 1px solid #ccc;
                    padding: 6px 10px;
                    text-align: left;
                }}
                th {{
                    background-color: #f0f0f0;
                }}
                tr:nth-child(even) {{
                    background-color: #fafafa;
                }}
            </style>
        </head>
        <body>
            <h1>Invoice – Order #{order.id}</h1>
            <div class="order-meta">
                <p><strong>Date:</strong> {order.created.strftime('%Y-%m-%d')}</p>
                <p><strong>Customer:</strong> {order.first_name} {order.last_name} &nbsp; | &nbsp; <strong>Email:</strong> {order.email}</p>
            </div>
        """

        for item in order.items.all():
            html += f"""
            <div class="item">
                <h2>{item.product_name}</h2>
                <h4>Selected Options</h4>
                <table>
                    <thead>
                        <tr><th>Label</th><th>Value</th></tr>
                    </thead>
                    <tbody>
            """

            selected_options = item.selected_options or {}
            for section, options_dict in selected_options.items():
                if section == "set":
                    single_item = options_dict.get("items", {})
                    name = single_item.get("name", "")
                    price = single_item.get("price_difference", "0.00")
                    display = f"{name} (+{price})" if price != "0.00" else name
                    html += f"<tr><td>{section.capitalize()}</td><td>{display}</td></tr>"
                else:
                    for label, option in options_dict.items():
                        name = option.get("name", "")
                        price = option.get("price_difference", "0.00")
                        display = f"{name} (+{price})" if price != "0.00" else name
                        html += f"<tr><td>{label.capitalize()}</td><td>{display}</td></tr>"

            html += "</tbody></table>"

            m = item.user_measurement
            if m:
                html += f"<p><strong>Fit Type:</strong> {m.get_fit_type_display()}</p>"
                html += '<div class="photos">'
                if m.photo_front:
                    html += f'<img src="{request.build_absolute_uri(m.photo_front.url)}" alt="Front" />'
                if m.photo_side:
                    html += f'<img src="{request.build_absolute_uri(m.photo_side.url)}" alt="Side" />'
                if m.photo_back:
                    html += f'<img src="{request.build_absolute_uri(m.photo_back.url)}" alt="Back" />'
                html += '</div>'

                html += "<h4>Measurements</h4><table><thead><tr><th>Part</th><th>Measurement (inch)</th></tr></thead><tbody>"
                for key, value in m.measurement_data.items():
                    html += f"<tr><td>{key.capitalize()}</td><td>{value}</td></tr>"
                html += "</tbody></table>"

            elif item.frozen_measurement_data:
                html += "<h4>Measurements (Frozen)</h4><table><thead><tr><th>Part</th><th>Value (cm)</th></tr></thead><tbody>"
                for key, value in item.frozen_measurement_data.items():
                    html += f"<tr><td>{key.capitalize()}</td><td>{value}</td></tr>"
                html += "</tbody></table>"

            html += "</div>"

        html += "</body></html>"

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename=invoice_{order_id}.pdf'
        HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf(response)
        return response

    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)
