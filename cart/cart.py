from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from store.models import Product
from .models import CartItem, CartSettings, Cart as CartModel  # Rename to avoid name clash
import json
import hashlib


def get_cart_settings():
    try:
        return CartSettings.objects.latest('id')
    except CartSettings.DoesNotExist:
        return CartSettings(free_shipping_threshold=Decimal('300.00'), gift_wrap_price=Decimal('5.00'))


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

        settings_obj = get_cart_settings()
        self.FREE_SHIPPING_THRESHOLD = settings_obj.free_shipping_threshold
        self.gift_wrap_price = settings_obj.gift_wrap_price
        self.gift_wrap = self.session.get('gift_wrap', False)

    def _split_cart_key(self, cart_key):
        if ':' in cart_key:
            return cart_key.split(':', 1)
        return cart_key, None

    def _calculate_extra_price(self, selected_options):
        extra_price = Decimal('0.00')

        if not selected_options:
            return extra_price

        seen_prices = set()

        for category, options in selected_options.items():
            if not isinstance(options, dict):
                continue

            # Skip unselected optional items
            #if category in ['vest', 'monogram', 'shirt_monogram', 'shirt'] and not options.get('price'):
            #    continue

            for key, option in options.items():
                if not isinstance(option, dict):
                    continue

                price_diff = option.get('price_difference')
                if price_diff:
                    unique_id = f"{category}_{key}"
                    if unique_id in seen_prices:
                        continue
                    try:
                        extra_price += Decimal(price_diff)
                        seen_prices.add(unique_id)
                    except Exception:
                        continue

        return extra_price



    def add(self, product, quantity=1, override_quantity=False, selected_options=None, customizations=None, delivery_date=None):
        product_id = str(product.id)
        options_key = self._generate_options_key(selected_options, customizations)
        cart_key = f"{product_id}:{options_key}"

        base_price = product.discounted_price or product.price
        extra_price = self._calculate_extra_price(selected_options)
        final_price = base_price + extra_price

        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'product_id': product.id,
                'quantity': 0,
                'price': str(final_price),
                'selected_options': selected_options or {},
                'customizations': customizations or {},
                'delivery_date': delivery_date,
            }

        if override_quantity:
            self.cart[cart_key]['quantity'] = quantity
        else:
            self.cart[cart_key]['quantity'] += quantity

        self.save()

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session['gift_wrap'] = self.gift_wrap
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        keys_to_remove = [k for k in self.cart if k.startswith(product_id + ':')]
        for k in keys_to_remove:
            del self.cart[k]
        self.save()

    def __iter__(self):
        product_ids = {
            self._split_cart_key(k)[0]
            for k in self.cart
            if self._split_cart_key(k)[0].isdigit()
        }

        products = Product.objects.filter(id__in=product_ids)
        products_map = {str(product.id): product for product in products}

        for cart_key, item in self.cart.items():
            product_id, _ = self._split_cart_key(cart_key)
            if not product_id.isdigit():
                continue

            product = products_map.get(product_id)
            if product:
                item = item.copy()
                item['product'] = product
                
                # ✅ Add delivery_date here
                delivery_days = getattr(product, 'delivery_days', 7) or 7
                delivery_date = datetime.today() + timedelta(days=delivery_days)
                item['delivery_date'] = delivery_date.strftime("%b %d, %Y")
                
                
                base_price = Decimal(item['price'])

                selected_options = item.get('selected_options', {})
                extra_price = self._calculate_extra_price(selected_options)

                base_price_with_extra = Decimal(item['price'])
                item['price'] = base_price_with_extra
                item['total_price'] = item['price'] * item['quantity']

                item['selected_options'] = selected_options
                item['customizations'] = item.get('customizations', {})
                item['cart_key'] = cart_key
                
                
                 # ✅ Add this debug print
                print(f"[DEBUG] Yielding cart item: {item}")

                yield item
                

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values() if isinstance(item, dict))
    
    

    def get_total_price(self):
        total = Decimal('0.00')
        for item in self.__iter__():
            total += item['total_price']
        if self.gift_wrap:
            total += self.gift_wrap_price
        return total

    def clear(self):
        if settings.CART_SESSION_ID in self.session:
            del self.session[settings.CART_SESSION_ID]
        if 'gift_wrap' in self.session:
            del self.session['gift_wrap']
        self.session.modified = True

    def get_free_shipping_data(self):
        total = self.get_total_price()
        qualified = total >= self.FREE_SHIPPING_THRESHOLD
        remaining = max(self.FREE_SHIPPING_THRESHOLD - total, Decimal('0.00'))
        progress = float(total / self.FREE_SHIPPING_THRESHOLD) if self.FREE_SHIPPING_THRESHOLD > 0 else 0.0
        progress = min(progress, 1.0)
        return {
            'progress': progress,
            'remaining': remaining,
            'qualified': qualified
        }

    def update(self, product, quantity, selected_options=None, customizations=None, delivery_date=None):
        product_id = str(product.id)
        options_key = self._generate_options_key(selected_options, customizations)
        cart_key = f"{product_id}:{options_key}"
        if cart_key in self.cart:
            self.cart[cart_key]['quantity'] = quantity
            if delivery_date:
                self.cart[cart_key]['delivery_date'] = delivery_date
            self.save()


    def get_item_total(self, product, selected_options=None, customizations=None):
        product_id = str(product.id)
        options_key = self._generate_options_key(selected_options, customizations)
        cart_key = f"{product_id}:{options_key}"
        if cart_key in self.cart:
            quantity = self.cart[cart_key]['quantity']
            price = Decimal(self.cart[cart_key]['price'])
            return price * quantity
        return Decimal('0.00')

    def toggle_gift_wrap(self, enable: bool):
        self.gift_wrap = enable
        self.save()

    def _normalize_dict(self, d):
        if not d:
            return {}
        normalized = {}
        for k in sorted(d.keys()):
            v = d[k]
            if isinstance(v, dict):
                normalized[k] = self._normalize_dict(v)
            elif isinstance(v, list):
                normalized[k] = [self._normalize_dict(i) if isinstance(i, dict) else str(i) for i in v]
            else:
                normalized[k] = str(v)
        return normalized

    def _generate_options_key(self, selected_options, customizations):
        normalized_options = self._normalize_dict(selected_options or {})
        normalized_custom = self._normalize_dict(customizations or {})
        options_str = json.dumps(normalized_options, sort_keys=True)
        custom_str = json.dumps(normalized_custom, sort_keys=True)
        combined = options_str + custom_str
        return hashlib.md5(combined.encode()).hexdigest()

    def get_product_by_key(self, cart_key):
        product_id, _ = self._split_cart_key(cart_key)
        if product_id.isdigit():
            try:
                return Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return None
        return None


def sync_session_to_db_cart(session_cart, user):
    if session_cart.session.session_key is None:
        session_cart.session.save()
    cart, created = CartModel.objects.get_or_create(cart_id=session_cart.session.session_key)

    for item in session_cart:
        product = item['product']
        selected_options = item.get('selected_options', {})
        customizations = item.get('customizations', {})
        quantity = item['quantity']
        base_price = item['price']

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            selected_options=selected_options,
            defaults={
                'quantity': quantity,
                'base_price': base_price,
                'customizations': customizations,
                'is_active': True,
            }
        )
        if not created:
            cart_item.quantity = quantity
            cart_item.base_price = base_price
            cart_item.customizations = customizations
            cart_item.is_active = True
            cart_item.save()

    return cart