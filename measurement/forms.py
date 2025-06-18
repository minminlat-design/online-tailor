from django import forms
from .models import UserMeasurement, MeasurementType
from django.core.exceptions import ValidationError


class DynamicMeasurementForm(forms.Form):
    fit_type = forms.ChoiceField(
        choices=UserMeasurement.FitType.choices,
        required=True,
        help_text="Select the fit type for this measurement set."
    )

    photo_front = forms.ImageField(required=False)
    photo_side = forms.ImageField(required=False)
    photo_back = forms.ImageField(required=False)

    def __init__(self, *args, instance=None, measurement_keys=None, **kwargs):
        self.instance = instance  # Optional: for editing
        self.measurement_keys = measurement_keys or []

        super().__init__(*args, **kwargs)

        # Get MeasurementType objects from keys
        measurements = MeasurementType.objects.filter(key__in=self.measurement_keys)
        self.measurement_map = {m.key: m for m in measurements}

        # Dynamically add FloatFields for each measurement type
        for mt in measurements:
            self.fields[mt.key] = forms.FloatField(
                label=mt.name,
                required=True,
                help_text=mt.description or '',
                widget=forms.NumberInput(attrs={'step': '0.1'})
            )
            # Attach the video URL or file path as a custom attribute
            self.fields[mt.key].video_source = mt.get_video_source()
            

        # Pre-fill form if editing existing instance
        if instance:
            self.initial['fit_type'] = instance.fit_type
            self.initial['photo_front'] = instance.photo_front
            self.initial['photo_side'] = instance.photo_side
            self.initial['photo_back'] = instance.photo_back
            for key in self.measurement_keys:
                self.initial[key] = instance.measurement_data.get(key, '')

    def clean(self):
        cleaned_data = super().clean()

        # Ensure at least one valid measurement was submitted
        if not any(cleaned_data.get(k) is not None for k in self.measurement_keys):
            raise ValidationError("Please enter at least one measurement value.")

        # Optional: validate numeric values here again if needed
        for key in self.measurement_keys:
            value = cleaned_data.get(key)
            if value is not None and not isinstance(value, (int, float)):
                raise ValidationError(f"Measurement '{key}' must be a number.")

        return cleaned_data

    def save(self, user):
        if not self.is_valid():
            raise ValidationError("Form data is invalid")

        measurement_data = {
            key: self.cleaned_data[key]
            for key in self.measurement_keys
            if key in self.cleaned_data
        }

        if self.instance:
            # Update existing instance
            self.instance.user = user
            self.instance.fit_type = self.cleaned_data.get('fit_type')
            self.instance.photo_front = self.cleaned_data.get('photo_front')
            self.instance.photo_side = self.cleaned_data.get('photo_side')
            self.instance.photo_back = self.cleaned_data.get('photo_back')
            self.instance.measurement_data = measurement_data
            self.instance.save()
            return self.instance
        else:
            # Create new instance
            instance = UserMeasurement.objects.create(
                user=user,
                fit_type=self.cleaned_data.get('fit_type'),
                photo_front=self.cleaned_data.get('photo_front'),
                photo_side=self.cleaned_data.get('photo_side'),
                photo_back=self.cleaned_data.get('photo_back'),
                measurement_data=measurement_data
            )
            return instance

