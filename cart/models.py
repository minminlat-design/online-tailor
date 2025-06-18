from django.db import models
from decimal import Decimal
from django.utils import timezone
import uuid
from measurement.models import UserMeasurement
from store.models import Product
from django.contrib.postgres.fields import JSONField
from django.contrib.auth import get_user_model

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








class CartItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Add this
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, null=True, blank=True)

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    gift_wrap = models.BooleanField(default=False)  # ✅ Optional gift wrap

    user_measurement = models.ForeignKey(
        UserMeasurement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Measurement set used for this item"
    )

    frozen_measurement_data = models.JSONField(blank=True, null=True)

    selected_options = models.JSONField(default=dict, blank=True)
    customizations = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def calculate_total_price(self):
        extra_price = Decimal('0')

        def extract_prices(data):
            nonlocal extra_price
            if isinstance(data, dict):
                for key, value in data.items():
                    if key == "price_difference":
                        try:
                            extra_price += Decimal(str(value))
                        except (TypeError, ValueError):
                            continue
                    else:
                        extract_prices(value)
            elif isinstance(data, list):
                for item in data:
                    extract_prices(item)

        extract_prices(self.selected_options)

        total = (self.base_price + extra_price) * self.quantity

        if self.gift_wrap:
            total += Decimal('5.00')

        return total


    def save(self, *args, **kwargs):
        self.total_price = self.calculate_total_price()
        if self.user_measurement and not self.frozen_measurement_data:
            self.frozen_measurement_data = self.user_measurement.measurement_data
        super().save(*args, **kwargs)
