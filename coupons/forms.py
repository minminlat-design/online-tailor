from django import forms

class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label='Coupon Code',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter coupon code'
        })
    )
