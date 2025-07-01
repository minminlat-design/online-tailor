from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    discount = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Percentage value (0 – 100).'
    )
    active = models.BooleanField(default=True)

    # ── NEW FIELDS ────────────────────────────────────────────────────────
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum redemptions (blank = unlimited)."
    )
    used_count = models.PositiveIntegerField(default=0)
    # ──────────────────────────────────────────────────────────────────────
    
    stripe_id = models.CharField(max_length=255, blank=True, null=True, help_text="Stripe coupon ID")


    # ── Display helpers ──────────────────────────────────────────────────
    def __str__(self):
        return self.code

    # ── Save hook ────────────────────────────────────────────────────────
    def save(self, *args, **kwargs):
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    # ── Business logic helpers ───────────────────────────────────────────
    def is_valid(self) -> bool:
        """
        Return True if the coupon:
        - is active,
        - is within the date window,
        - has not exceeded its usage limit.
        """
        now = timezone.now()
        within_dates = self.valid_from <= now <= self.valid_to
        under_limit = (
            self.usage_limit is None or      # unlimited
            self.used_count < self.usage_limit
        )
        return self.active and within_dates and under_limit

    def increment_usage(self, save: bool = True) -> None:
        """
        Call this once you’ve successfully attached the coupon to an order.
        """
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            raise ValidationError("Usage limit reached for this coupon.")
        self.used_count += 1
        if save:
            self.save(update_fields=["used_count"])

    # ── Model‑level validation ───────────────────────────────────────────
    def clean(self):
        if self.valid_to < self.valid_from:
            raise ValidationError(
                {"valid_to": "The 'valid to' date cannot be earlier than 'valid from'."}
            )
