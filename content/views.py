from datetime import datetime
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages

from .models import StaticPage, GalleryImage, AboutPage, ContactPage
from home.models import ShopGram
from .forms import AppointmentForm


@csrf_protect
def static_page_detail(request, slug):
    page = get_object_or_404(StaticPage, slug=slug, published=True)

    # Map slugs to specific templates
    template_map = {
        'gallery': 'content/gallery.html',
        'contact': 'content/contact.html',
        'make-an-appointment': 'content/appointment.html',
        'about-us': 'content/about.html',
    }

    template_name = template_map.get(slug)
    if not template_name:
        raise Http404("No template for this page.")

    context = {'page': page}

    if slug == 'gallery':
        images = GalleryImage.objects.filter(is_visible=True).order_by('order', '-created_at')
        paginator = Paginator(images, 8)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj

    elif slug == 'about-us':
        about_page = AboutPage.objects.first()
        shop_gram_items = ShopGram.objects.filter(is_active=True).prefetch_related('products').order_by('order', '-created_at')[:6]
        context['about_page'] = about_page
        context['shop_gram_items'] = shop_gram_items

    elif slug == 'contact':
        contact_page = ContactPage.objects.filter(is_active=True).first()
        context['contact_page'] = contact_page
        
        
    elif slug == 'make-an-appointment':
        if request.method == 'POST':
            print(request.POST)  # <-- Add this temporarily
            form = AppointmentForm(request.POST)
            if form.is_valid():
                appointment = form.save()

                # Format preferred datetime if available
                preferred_dt = None
                if appointment.preferred_date and appointment.preferred_time:
                    preferred_dt = datetime.combine(appointment.preferred_date, appointment.preferred_time)
                    preferred_dt_str = preferred_dt.strftime('%Y-%m-%d %I:%M %p')
                else:
                    preferred_dt_str = 'N/A'

                # Send email to staff
                subject = 'New Appointment Request'
                message = (
                    f"New appointment submitted:\n\n"
                    f"Name: {appointment.first_name} {appointment.last_name}\n"
                    f"Email: {appointment.email}\n"
                    f"Referral Source: {appointment.referral_source}\n"
                    f"Existing Customer: {'Yes' if appointment.existing_customer else 'No'}\n"
                    f"Preferred Location: {appointment.preferred_location}\n"
                    f"Preferred Date & Time: {preferred_dt_str}\n"
                )
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, ['minminlat.shirt@gmail.com'])

                # Confirmation email to user
                send_mail(
                    subject='Appointment Confirmation',
                    message=(
                        f"Hi {appointment.first_name},\n\n"
                        f"Thank you for booking an appointment with us. We’ve received your request and will be in touch soon.\n\n"
                        f"Appointment details:\n"
                        f"Location: {appointment.preferred_location}\n"
                        f"Date & Time: {preferred_dt_str}\n\n"
                        f"Best regards,\nYour Company Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[appointment.email],
                )

                messages.success(request, "Thank you for making an appointment. We will contact you soon!")
                return redirect('content:make_appointment_success')
        else:
            form = AppointmentForm()
            
         # Add this dictionary mapping pk -> Location object
        location_dict = {str(loc.pk): loc for loc in form.fields['preferred_location'].queryset}
        context['form'] = form
        context['location_dict'] = location_dict
          


    return render(request, template_name, context)


@csrf_protect
def contact_form_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        send_mail(
            subject=f"Contact Form Submission from {name}",
            message=message,
            from_email=email,
            recipient_list=['latkolat@gmail.com'],
        )
        messages.success(request, "Thanks! Your message has been sent.")
        return redirect('content:static_page_detail', slug='contact')


def make_appointment_success(request):
    return render(request, 'content/appointment_success.html')
