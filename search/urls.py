from django.urls import path
from search import views


app_name = "search"

urlpatterns = [
    path('', views.search_view, name='search'),
]
