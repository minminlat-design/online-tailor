import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from orders.models import Order
from .tasks import payment_completed
from store.models import Product
from store.recommender import Recommender




@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        if session.get('mode') == 'payment' and session.get('payment_status') == 'paid':
            try:
                order = Order.objects.get(id=session.get('client_reference_id'))
                order.paid = True
                order.status = 'processing'
                order.stripe_id = session.get('payment_intent')
                order.save()

                product_ids = order.items.values_list('product_id', flat=True)
                products = Product.objects.filter(id__in=product_ids)
                
                r = Recommender()
                try:
                    r.products_bought(products)
                except Exception as e:
                    # log but do not block payment confirmation
                    print(f"Redis recommendation update failed: {e}")

                payment_completed.delay(order.id)
                print(f"[Webhook] Order {order.id} marked as paid.")
            except Order.DoesNotExist:
                return HttpResponse(status=404)

    return HttpResponse(status=200)
