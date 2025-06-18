from django.contrib.auth import views as auth_views
from django.urls import path
from accounts import views
from accounts.forms import EmailAuthenticationForm
from accounts.views import CustomLoginView, CustomPasswordResetView, load_account_section, account_details



urlpatterns = [
    path('register/', views.register, name='register'),
    
    # login / logout urls
    #path('login/', auth_views.LoginView.as_view(template_name='account/login.html',
    #                                            authentication_form=EmailAuthenticationForm), name='login'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Change password urls
    path('account/details/', views.account_details, name='account_details'),
    
    # Password reset urls
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),



   
    path('', views.dashboard, name='dashboard'),
    
    # dashboard section ajax call
    path('section/<str:section>/', load_account_section, name='account_section'),
    path('account/update-measurements/', views.update_measurements, name='update_measurements'),

    


       
    
]
