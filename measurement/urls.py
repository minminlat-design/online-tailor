# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('create/<str:product_type_name>/', views.create_measurement, name='create_measurement'),
    path('edit/<int:pk>/', views.edit_measurement, name='edit_measurement'),
    #path("cart/measurement/", views.measurement_form_view, name="measurement_form_view"),

]
