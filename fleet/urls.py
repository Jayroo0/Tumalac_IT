# fleet/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views  # Underline clears once used below!
from . import views

urlpatterns = [
    
    # 1. Main public dashboard homepage
    path('', views.homepage, name='homepage'),
    
    # 2. Secure Operator Logistics Dashboard panel
    path('dashboard/staff/', views.admin_logistic_dashboard, name='admin_logistic_dashboard'),
    
    # 3. Touch Screen Mechanic Dashboard console
    path('dashboard/repairman/', views.repairman_dashboard, name='repairman_dashboard'),


    # Using auth_views here satisfies the import checker:
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    
    path('logout/', views.custom_logout, name='logout'),
    path('redirect/', views.dashboard_redirect, name='dashboard_redirect'),
]