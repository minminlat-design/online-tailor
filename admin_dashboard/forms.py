from django import forms
from orders.models import Order, OrderItem

class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class OrderItemMeasurementForm(forms.ModelForm):
    frozen_measurement_data = forms.JSONField(widget=forms.Textarea)
    
    class Meta:
        model = OrderItem
        fields = ['frozen_measurement_data']  # Or any editable measurement fields you want
