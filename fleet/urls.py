# fleet/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Main Landing & Router Switchboard
    path('', views.homepage, name='homepage'),
    path('redirect/', views.dashboard_redirect, name='dashboard_redirect'),
    
    # Administrative & Logistics Dashboards
    path('dashboard/staff/', views.admin_logistic_dashboard, name='admin_logistic_dashboard'),
    
    # Workshop Matrix Dashboards (Land vs. Sea)
    path('dashboard/repairman/', views.repairman_dashboard, name='repairman_dashboard'),
    path('dashboard/land-workshop/', views.repairman_dashboard, name='land_workshop_dashboard'), 
    path('dashboard/land-mobile-workshop/', views.land_mobile_dashboard, name='land_mobile_dashboard'),
    path('dashboard/seacraft/', views.seacraft_dashboard, name='seacraft_dashboard'),
    path('dashboard/seacraft/', views.seacraft_dashboard, name='maritime_dashboard'),
    # ADD THIS LINE HERE TO CHASE THE NOREVERSEMATCH ERROR AWAY:
    path('maintenance/fix/<int:issue_id>/', views.process_fix_issue, name='process_fix_issue'),
    
    # Authentication Management
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('custom-logout-alias/', views.custom_logout, name='custom_logout'),
]