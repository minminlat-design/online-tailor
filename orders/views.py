from django.db import transaction
from decimal import Decimal
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




logger = logging.getLogger(__name__)













def create_order_from_cart(user, shipping_data):
    """
    shipping_data is a dict with keys like first_name, last_name, email, address, postal_code, city
    """
    cart_items = CartItem.objects.filter(user=user, is_active=True)
    if not cart_items.exists():
        raise ValueError("Cart is empty")

    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            first_name=shipping_data['first_name'],
            last_name=shipping_data['last_name'],
            email=shipping_data['email'],
            address=shipping_data['address'],
            postal_code=shipping_data['postal_code'],
            city=shipping_data['city'],
            phone=shipping_data['phone'],        # ✅ Add this
            country=shipping_data['country'],    # ✅ Add this
            paid=False,
            status='pending',
            total_price=Decimal('0')
        )

        total_price = Decimal('0')
        for ci in cart_items:
            
            print(f"[DEBUG] frozen_measurement_data for {ci.product.name}: {ci.frozen_measurement_data} ({type(ci.frozen_measurement_data)})")
            frozen_data = ci.frozen_measurement_data or {}


            oi = OrderItem.objects.create(
                order=order,
                product=ci.product,
                product_name=ci.product.name,
                quantity=ci.quantity,
                base_price=ci.base_price,
                total_price=ci.total_price,
                gift_wrap=ci.gift_wrap,
                #frozen_measurement_data=ci.frozen_measurement_data,
                frozen_measurement_data=frozen_data,
                selected_options=ci.selected_options,
                customizations=ci.customizations,
                user_measurement=ci.user_measurement,

            )
            print(f"[DEBUG] Saved OrderItem frozen data: {oi.frozen_measurement_data}")

            total_price += oi.total_price

            ci.is_active = False
            ci.save()
            
        print(f"[DEBUG] Copying frozen data to OrderItem: {ci.frozen_measurement_data}")


        order.total_price = total_price
        order.save()

    return order




@login_required
def shipping_info_view(request):
    cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart:cart_detail')

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
                'phone': data['phone'],        # ✅ Add this
                'country': data['country'],    # ✅ Add this
            }
            print("[DEBUG] Shipping info saved:", request.session['shipping_info'])
            return redirect('orders:review_order')  # Next step
    else:
        # Use session data to pre-fill the form if available
        initial_data = request.session.get('shipping_info')
        form = ShippingForm(initial=initial_data)

    subtotal = sum(item.total_price for item in cart_items)

    return render(request, 'orders/shipping_info.html', {
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
    })



stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def review_order_view(request):
    shipping_info = request.session.get('shipping_info')
    if not shipping_info:
        messages.error(request, "Shipping information is missing.")
        return redirect('orders:shipping_info')

    cart_items = CartItem.objects.filter(user=request.user, is_active=True)
    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart:cart_detail')

    subtotal = sum(item.total_price for item in cart_items)

    if request.method == 'POST':
        # Create Order
        order = create_order_from_cart(request.user, shipping_info)
        
        # Trigger async email
        order_created.delay(order.id)

        # Create Stripe Checkout Session
        line_items = [
            {
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': int(item.total_price * 100),  # in cents
                    'product_data': {
                        'name': item.product_name,
                    },
                },
                'quantity': item.quantity,
            } for item in order.items.all()
        ]

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('orders:payment_success')),
            cancel_url=request.build_absolute_uri(reverse('orders:payment_cancel')),
            metadata={'order_id': order.id},
            client_reference_id=order.id 
        )

        return redirect(checkout_session.url, code=303)

    return render(request, 'orders/review_order.html', {
        'shipping_info': shipping_info,
        'cart_items': cart_items,
        'subtotal': subtotal,
    })







 
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
