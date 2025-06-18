from twilio.rest import Client
from django.conf import settings

def send_sms(to_number, message):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    message = client.messages.create(
        body=message,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to_number  # Must be in +[country code][number] format, e.g. +14155552671
    )
    print(f"Sending SMS to {to_number}: {message}")  # <-- Debug print
    
    return message.sid
