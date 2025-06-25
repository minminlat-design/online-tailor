from django.contrib import admin
from .models import NewsletterSignup



@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ['email', 'subscribed_at']