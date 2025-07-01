from django.db import models, transaction
from decimal import Decimal
from django.utils import timezone
import uuid
from measurement.models import UserMeasurement
from store.models import Product
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model
       # ← make sure this import path matches your project


User = get_user_model()



class Cart(models.Model):
    cart_id = models.CharField(max_length=250, blank=True, unique=True)
    date_added = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)  # Track updates

    def save(self, *args, **kwargs):
        if not self.cart_id:
            self.cart_id = str(uuid.uuid4())
        super().save(*args, **kwargs)




# Free shipping threshold and gift wrap price fixing
class CartSettings(models.Model):
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('300.00')
    )
    gift_wrap_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('5.00')
    )

    def __str__(self):
        return f"Cart Settings (Free shipping over ${self.free_shipping_threshold}, Gift wrap ${self.gift_wrap_price})"

    class Meta:
        verbose_name = "Cart Setting"
        verbose_name_plural = "Cart Settings"








def current_wrap_fee() -> Decimal:
    """
    Returns the active gift‑wrap unit price.
    Falls back to 5.00 USD if no CartSettings record exists.
    """
    try:
        return CartSettings.objects.latest("id").gift_wrap_price
    except CartSettings.DoesNotExist:
        return Decimal("5.00")


class CartItem(models.Model):
    # -------------------------------- Core relations --------------------------------
    user  = models.ForeignKey(User, on_delete=models.CASCADE,  null=True, blank=True)
    cart  = models.ForeignKey("cart.Cart", on_delete=models.CASCADE, null=True, blank=True)

    product     = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity    = models.PositiveIntegerField(default=1)
    is_active   = models.BooleanField(default=True)

    # -------------------------------- Pricing ---------------------------------------
    base_price  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    gift_wrap   = models.BooleanField(default=False)   # per‑item flag ✅

    # -------------------------------- Measurements ----------------------------------
    user_measurement = models.ForeignKey(
        UserMeasurement,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Measurement set used for this item"
    )
    frozen_measurement_data = models.JSONField(blank=True, null=True)

    # -------------------------------- Options / custom --------------------------------
    selected_options = models.JSONField(default=dict, blank=True)
    customizations   = models.JSONField(blank=True, null=True)

    # -------------------------------------------------------------------------------
    def __str__(self) -> str:
        return f"{self.product.name} × {self.quantity}"

    # -------------------------------------------------------------------------------
    # Pricing helpers
    # -------------------------------------------------------------------------------
    def _selected_options_extra(self) -> Decimal:
        """
        Recursively sums positive `price_difference` values from `selected_options`.
        """
        extra_price = Decimal("0")

        def walk(node):
            nonlocal extra_price
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "price_difference":
                        try:
                            extra_price += Decimal(str(v))
                        except (TypeError, ValueError):
                            pass
                    else:
                        walk(v)
            elif isinstance(node, list):
                for itm in node:
                    walk(itm)

        walk(self.selected_options)
        return extra_price

    
    def calculate_total_price(self) -> Decimal:
        """
        (base + selected‑option extras) × quantity
        Gift‑wrap is handled at the cart/order level; do NOT add it here.
        """
        extra_price = Decimal("0")

        def walk(node):
            nonlocal extra_price
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "price_difference":
                        try:
                            extra_price += Decimal(str(v))
                        except (TypeError, ValueError):
                            pass
                    else:
                        walk(v)
            elif isinstance(node, list):
                for itm in node:
                    walk(itm)

        walk(self.selected_options)

        total = (self.base_price + extra_price) * self.quantity
        return total.quantize(Decimal("0.01"))
    # -------------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------------
    def save(self, *args, **kwargs):
        self.total_price = self.calculate_total_price()

        # Freeze measurements snapshot if not already frozen
        if self.user_measurement and not self.frozen_measurement_data:
            self.frozen_measurement_data = self.user_measurement.measurement_data

        super().save(*args, **kwargs)
