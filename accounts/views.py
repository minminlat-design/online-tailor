from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy

from cart.models import CartItem
from .forms import AccountDetailsForm, EmailAuthenticationForm, RegistrationForm
from django.contrib.auth import login, update_session_auth_hash
from accounts.models import Account
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.messages import constants as message_constants
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.views import PasswordResetView, LoginView
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_str as force_text
from django.conf import settings
from orders.models import Order

from measurement.forms import DynamicMeasurementForm
from measurement.models import ProductTypeMeasurement, UserMeasurement, MeasurementType



def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, "Your account has been activated successfully!")
        return redirect('dashboard')
    else:
        messages.error(request, "Activation link is invalid or expired.")
        return redirect('login')


def send_activation_email(request, user):
    current_site = get_current_site(request)
    subject = 'Activate your account'
    message = render_to_string('registration/account_activation_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': default_token_generator.make_token(user),
    })
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )



def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            username = email.split("@")[0]

            # Create user without is_active argument
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password,
            )
            
            # Set user as inactive until they activate via email
            user.is_active = False
            user.save()

            send_activation_email(request, user)

            messages.success(request, 'Registration successful! Please check your email to activate your account.')

            return redirect('login')

    else:
        form = RegistrationForm()

    return render(
        request,
        'account/register.html',
        {
            'form': form,
            'next': request.GET.get('next', '')  # To preserve next param for after login
        }
    )
  

@login_required
def update_measurements(request):
    instance = UserMeasurement.objects.filter(user=request.user).first()

    if instance:
        cart_items = CartItem.objects.filter(user=request.user, user_measurement=instance)

        product_types = set()
        for item in cart_items:
            pt = getattr(item.product, 'product_type', None)
            if pt:
                product_types.add(pt)

        measurement_keys = []
        for pt in product_types:
            keys = ProductTypeMeasurement.objects.filter(product_type=pt).values_list('measurement_type__key', flat=True)
            measurement_keys.extend(keys)
        measurement_keys = list(set(measurement_keys))
    else:
        measurement_keys = None  # fallback to all keys or empty list

    if request.method == 'POST':
        form = DynamicMeasurementForm(request.POST, request.FILES, instance=instance, measurement_keys=measurement_keys)
        if form.is_valid():
            updated = form.save(user=request.user)

            # update CartItems frozen data
            related_items = CartItem.objects.filter(user=request.user, user_measurement=updated)
            for item in related_items:
                item.frozen_measurement_data = {
                    "fit_type": updated.fit_type,
                    "data": updated.measurement_data,
                    "photos": {
                        "front": updated.photo_front.url if updated.photo_front else None,
                        "side": updated.photo_side.url if updated.photo_side else None,
                        "back": updated.photo_back.url if updated.photo_back else None,
                    }
                }
                item.save()

            messages.success(request, "Measurements updated successfully.")
            return redirect(f"{reverse('dashboard')}?section=measurements")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DynamicMeasurementForm(instance=instance, measurement_keys=measurement_keys)

    return render(request, 'account/partials/measurements.html', {'form': form})





@login_required
def dashboard(request):
    
    return render(
        request,
        'account/dashboard.html',
        {
            'section': 'dashboard',
            
        }
    )
    


@login_required
def load_account_section(request, section):
    
    orders_count = Order.objects.filter(user_id=request.user.id).count()
    
    
    
    if section == 'orders':
        print("Loading orders section")  # <--- add this
        template = 'account/partials/orders.html'
        orders = Order.objects.filter(user=request.user).prefetch_related('items')
        context = {
            'orders': orders
        }
    elif section.startswith('order_detail_'):
        order_id = section.replace('order_detail_', '')
        order = get_object_or_404(Order, id=order_id, user=request.user)
        template = 'account/partials/order_detail.html'
        context = {'order': order}
        
    elif section == 'address':
        template = 'account/partials/address.html'
        context = {}
    elif section == 'account_details':
        template = 'account/partials/account_details.html'
        context = {
            'form': AccountDetailsForm(user=request.user),
            'DEFAULT_MESSAGE_LEVELS': message_constants

        }
    elif section == 'measurements':
        # Get all available measurement keys (sorted, optional)
        measurement_keys = list(MeasurementType.objects.values_list('key', flat=True))

        instance = UserMeasurement.objects.filter(user=request.user).first()
        form = DynamicMeasurementForm(instance=instance, measurement_keys=measurement_keys)

        template = 'account/partials/measurements.html'
        context = {'form': form}

        
    else:  # default to dashboard
        template = 'account/partials/dashboard.html'
        
        context = {
            'orders_count': orders_count,
        }

    return render(request, template, context)

    


# Password change
@login_required
def account_details(request):
    if request.method == 'POST':
        form = AccountDetailsForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Account updated successfully.'})

            messages.success(request, 'Account updated successfully.')
            return redirect('dashboard')
        else:
            # Handle AJAX request with rendered HTML
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                rendered_html = render_to_string('account/partials/account_details.html', {
                    'form': form,
                    'DEFAULT_MESSAGE_LEVELS': message_constants
                }, request=request)
                return JsonResponse({'success': False, 'html': rendered_html}, status=400)

            messages.error(request, 'Please correct the errors below.')
    else:
        form = AccountDetailsForm(request.user)

    return render(request, 'account/partials/account_details.html', {
        'form': form,
        'DEFAULT_MESSAGE_LEVELS': message_constants
    })



class CustomPasswordResetView(PasswordResetView):
    template_name = 'account/login.html'
    email_template_name = 'registration/password_reset_email.html'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, (
            
            "We’ve emailed you instructions for setting your password, if an account exists "
            "with the email you entered. You should receive them shortly. "
            "If you don’t receive an email, please make sure you’ve entered the address you registered with, "
            "and check your spam folder."
        ))
        return response
    
    def get_success_url(self):
        # Redirect back with a query param to tell template to show reset block
        return reverse_lazy('password_reset') + '?reset=1'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add a flag to show the reset form if 'reset=1' param present
        context['show_reset'] = self.request.GET.get('reset') == '1'
        context['login_form'] = AuthenticationForm(self.request)
        context['reset_form'] = context.get('form', PasswordResetForm())
        return context
    


class CustomLoginView(LoginView):
    template_name = 'account/login.html'
    authentication_form = EmailAuthenticationForm

    def form_invalid(self, form):
        messages.error(self.request, "Your email and password didn't match. Please try again.")
        return super().form_invalid(form)
    
    