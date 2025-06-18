from django import forms
from .models import Account
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model


user = get_user_model


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))
    
    def confirm_login_allowed(self, user):
        if not user.is_active:
            raise forms.ValidationError("This account is inactive.", code="inactive")



class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)  
     
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'email', 'password']
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm = cleaned_data.get('confirm_password')
        
        if password and confirm and password != confirm:
            raise forms.ValidationError('Password and confirm password do not match')
        return cleaned_data
        
        




class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'email']



class AccountDetailsForm(forms.Form):
    # Embed user update fields
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    
    # Embed password fields (optional)
    old_password = forms.CharField(widget=forms.PasswordInput(), required=False)
    new_password1 = forms.CharField(widget=forms.PasswordInput(), required=False)
    new_password2 = forms.CharField(widget=forms.PasswordInput(), required=False)

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        # Set initial values for user info fields
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email

    def clean(self):
        cleaned_data = super().clean()

        old_password = cleaned_data.get('old_password')
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        # If any password field filled, validate password change fields
        if old_password or new_password1 or new_password2:
            if not old_password:
                self.add_error('old_password', 'Please enter your current password.')
            if new_password1 != new_password2:
                self.add_error('new_password2', 'New passwords do not match.')

            # Verify old password
            if old_password and not self.user.check_password(old_password):
                self.add_error('old_password', 'Incorrect current password.')

        return cleaned_data

    def save(self):
        # Save user info fields
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        self.user.save()

        # If password fields are filled, change password
        if self.cleaned_data.get('new_password1'):
            self.user.set_password(self.cleaned_data['new_password1'])
            self.user.save()