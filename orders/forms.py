# orders/forms.py
from django import forms
from .constants import COUNTRY_CHOICES

class ShippingForm(forms.Form):

    
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)  # New field
    address = forms.CharField(max_length=250)
    postal_code = forms.CharField(max_length=20)
    city = forms.CharField(max_length=100)
    country = forms.ChoiceField(choices=COUNTRY_CHOICES)
