# fleet/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main Dashboards
    path('', views.homepage, name='homepage'),
    path('dashboard/staff/', views.admin_logistic_dashboard, name='admin_logistic_dashboard'),
    path('dashboard/repairman/', views.repairman_dashboard, name='repairman_dashboard'),
    path('redirect/', views.dashboard_redirect, name='dashboard_redirect'),

    # Authentication Route Rules
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    
    # Dual-named alias protection prevents breaking dashboard layout forms
    path('logout/', views.custom_logout, name='logout'),
    path('custom-logout-alias/', views.custom_logout, name='custom_logout'),
]