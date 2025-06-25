from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from .models import NewsletterSignup, Question
from django.views.decorators.csrf import csrf_protect




@require_POST
def newsletter_subscribe(request):
    email = request.POST.get('email')
    if not email:
        return JsonResponse({'status': 'error', 'message': 'Email is required'}, status=400)

    obj, created = NewsletterSignup.objects.get_or_create(email=email)

    if created:
        # Send confirmation email
        try:
            send_mail(
                subject="Thanks for subscribing!",
                message="Hi! Thanks for subscribing to our newsletter. We'll keep you posted.",
                from_email=None,  # Uses DEFAULT_FROM_EMAIL in settings.py
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error or handle it as needed, but still return success for subscription
            print(f"Error sending email: {e}")

        return JsonResponse({'status': 'success', 'message': 'Thanks! We’ll keep you posted.'})
    else:
        return JsonResponse({'status': 'exists', 'message': 'You are already subscribed.'})





@csrf_protect
@require_POST
def submit_question(request):
    name = request.POST.get('name')
    email = request.POST.get('email')
    phone = request.POST.get('phone', '')
    message = request.POST.get('message')

    if not name or not email or not message:
        return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)

    # Save question to the database
    Question.objects.create(
        name=name,
        email=email,
        phone=phone,
        message=message,
    )

    # Compose email content
    subject = f"Ask a Question: {name}"
    email_message = f"""
New question received:

Name: {name}
Email: {email}
Phone: {phone or 'Not provided'}

Message:
{message}
""".strip()

    # Send email
    send_mail(
        subject=subject,
        message=email_message,
        from_email='latkolat@gmail.com',
        recipient_list=['minminlat.shirt@gmail.com'],  # Update as needed
        fail_silently=False,
    )

    return JsonResponse({'status': 'success', 'message': 'Thank you! We will respond shortly.'})