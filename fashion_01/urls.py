"""
URL configuration for fashion_01 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('blog/', include('blog.urls', namespace='blog')),
    path('', include('home.urls', namespace='home')),
    path('cart/', include('cart.urls', namespace='cart')),
    #path('wishlist/', include('wishlist.urls', namespace='wishlist')),
    path('store/', include('store.urls', namespace='store')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('search/', include('search.urls', namespace='search')),
    path('account/', include('accounts.urls')),
    path('measurements/', include('measurement.urls')),
    path('orders/', include('orders.urls', namespace='orders')),
    path('admin-panel/', include('admin_dashboard.urls', namespace='admin_dashboard')),
    
    path('', include('content.urls', namespace='content')),
    
    path('newsletter/', include('newsletter.urls', namespace='newsletter')),
   


   
]

if settings.DEBUG:
    urlpatterns += static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
)
