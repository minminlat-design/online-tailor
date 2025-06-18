from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    # Specific URLs first
    path('make-an-appointment/success/', views.make_appointment_success, name='make_appointment_success'),
    path('contact/submit/', views.contact_form_view, name='contact_form'),

    # General slug match last
    path('<slug:slug>/', views.static_page_detail, name='static_page_detail'),
]
