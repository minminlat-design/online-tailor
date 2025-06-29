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

    navbar_static_pages = StaticPage.objects.filter(published=True, show_in_navbar=True).order_by('order', 'title')

    template_map = {
        'gallery': 'content/gallery.html',
        'contact': 'content/contact.html',
        'make-an-appointment': 'content/appointment.html',
        'about-us': 'content/about.html',
        'shipping-delivery': 'content/shipping_delivery.html',  
        'delivery-return': 'content/delivery_return.html',  
        'privacy-policy': 'content/privacy_policy.html',
        'terms-and-conditions': 'content/terms_conditions.html',
        'faq': 'content/faq.html',         
    }

    template_name = template_map.get(slug)
    if not template_name:
        raise Http404("No template for this page.")

    context = {'page': page, 'navbar_static_pages': navbar_static_pages}

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
            form = AppointmentForm(request.POST)
            if form.is_valid():
                appointment = form.save()

                preferred_dt_str = 'N/A'
                if appointment.preferred_date and appointment.preferred_time:
                    preferred_dt = datetime.combine(appointment.preferred_date, appointment.preferred_time)
                    preferred_dt_str = preferred_dt.strftime('%Y-%m-%d %I:%M %p')

                # send emails (omitted here for brevity)...

                messages.success(request, "Thank you for making an appointment. We will contact you soon!")
                return redirect('content:make_appointment_success')
        else:
            form = AppointmentForm()

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

