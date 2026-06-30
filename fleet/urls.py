# fleet/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('portal/dispatch/', views.dashboard_router, name='dashboard_portal'),
    path('portal/logout/', views.custom_user_logout, name='custom_logout'), # 👈 Add this clear path
    path('repair/', views.repairman_dashboard, name='repairman_dashboard'),
    path('maritime/', views.seacraft_dashboard, name='seacraft_dashboard'),
    path('logistics/', views.logistics_dashboard, name='logistics_dashboard'),
    path('api/rfid-trigger/', views.rfid_sensor_trigger, name='api_rfid_trigger'),
]