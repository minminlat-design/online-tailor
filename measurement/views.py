# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import DynamicMeasurementForm
from .models import MeasurementType, ProductType, UserMeasurement
from django.contrib.auth.decorators import login_required




def get_measurement_keys_for_product_type(product_type_name):
    """
    Utility to get required measurement keys based on product type.
    You could customize this based on your business logic.
    """
    try:
        product_type = ProductType.objects.get(name__iexact=product_type_name)
        return product_type.measurements.values_list('measurement_type__key', flat=True)
    except ProductType.DoesNotExist:
        return []


@login_required
def create_measurement(request, product_type_name="shirt"):
    measurement_keys = get_measurement_keys_for_product_type(product_type_name)

    if request.method == "POST":
        form = DynamicMeasurementForm(request.POST, request.FILES, measurement_keys=measurement_keys)
        if form.is_valid():
            form.save(user=request.user)
            return redirect("measurement_list")  # adjust this to your app’s navigation
    else:
        form = DynamicMeasurementForm(measurement_keys=measurement_keys)

    return render(request, "measurements/create_measurement.html", {
        "form": form,
        "title": "Create Measurement",
    })


@login_required
def edit_measurement(request, pk):
    instance = get_object_or_404(UserMeasurement, pk=pk, user=request.user)
    measurement_keys = instance.measurement_data.keys()

    if request.method == "POST":
        form = DynamicMeasurementForm(
            request.POST, request.FILES,
            instance=instance,
            measurement_keys=measurement_keys
        )
        if form.is_valid():
            form.save(user=request.user)
            return redirect("measurement_list")  # adjust as needed
    else:
        form = DynamicMeasurementForm(
            instance=instance,
            measurement_keys=measurement_keys
        )

    return render(request, "measurements/edit_measurement.html", {
        "form": form,
        "title": "Edit Measurement",
        "instance": instance,
    })


