from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Q, F  # ← Added F import here

from .forms import CouponApplyForm
from .models import Coupon

@require_POST
def coupon_apply(request):
    """Validate a coupon code sent via POST and stash its PK in the session."""
    now = timezone.now()
    form = CouponApplyForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please enter a valid coupon code.")
        return redirect("cart:cart_detail")

    code = form.cleaned_data["code"]

    # Look up active, valid, and not overused coupon
    try:
        coupon = Coupon.objects.filter(
            code__iexact=code,
            valid_from__lte=now,
            valid_to__gte=now,
            active=True
        ).filter(
            Q(usage_limit__isnull=True) | Q(used_count__lt=F("usage_limit"))
        ).get()

        request.session["coupon_id"] = coupon.id
        messages.success(request, f"Coupon “{coupon.code}” applied!")

    except Coupon.DoesNotExist:
        request.session["coupon_id"] = None
        messages.error(request, "That coupon code is invalid, expired, or fully used.")

    return redirect("cart:cart_detail")
