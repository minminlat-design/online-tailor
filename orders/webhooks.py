import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from orders.models import Order
from .tasks import payment_completed


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')  # safer with .get()
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    # ✅ Handle successful checkout session
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        if session.get('mode') == 'payment' and session.get('payment_status') == 'paid':
            try:
                order = Order.objects.get(id=session.get('client_reference_id'))
                order.paid = True
                order.status = 'processing'  # Optional but helpful
                order.stripe_id = session.get('payment_intent')  # ✅ Save payment intent
                order.save()
                # launch asynchronous task
                payment_completed.delay(order.id)
                
                print(f"[Webhook] Order {order.id} marked as paid.")
            except Order.DoesNotExist:
                return HttpResponse(status=404)
            
            

    return HttpResponse(status=200)
