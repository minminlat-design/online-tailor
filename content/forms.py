from django import forms
from .models import Appointment, Location
from datetime import date, datetime

class AppointmentForm(forms.ModelForm):
    existing_customer = forms.BooleanField(
        required=False,
        label="Are you an existing customer?"
    )

    preferred_location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Where do you want to meet up? *"
    )

    preferred_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
        }),
        label="Preferred Date for Appointment (In Store only)"
    )

    preferred_time = forms.TimeField(
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-control',
        }),
        label="Preferred Time for Appointment (In Store only)"
    )

    class Meta:
        model = Appointment
        fields = [
            'first_name',
            'last_name',
            'email',
            'referral_source',
            'existing_customer',
            'preferred_location',
            'preferred_date',
            'preferred_time',
        ]

    def clean(self):
        cleaned_data = super().clean()
        location = cleaned_data.get('preferred_location')
        date_ = cleaned_data.get('preferred_date')
        time_ = cleaned_data.get('preferred_time')

        if location and location.location_type == Location.IN_STORE:
            if not date_:
                self.add_error('preferred_date', 'Please provide a preferred date for in-store appointments.')
            if not time_:
                self.add_error('preferred_time', 'Please provide a preferred time for in-store appointments.')

            # Optional: validate date is not in the past
            if date_ and date_ < date.today():
                self.add_error('preferred_date', 'Preferred date cannot be in the past.')

            # Optional: if date is today, ensure time is in the future
            if date_ == date.today() and time_ and time_ <= datetime.now().time():
                self.add_error('preferred_time', 'Preferred time must be later than the current time.')

        else:
            # If not in-store, clear date and time to avoid accidental data saving
            cleaned_data['preferred_date'] = None
            cleaned_data['preferred_time'] = None

        return cleaned_data
