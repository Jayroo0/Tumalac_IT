# fleet/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('dashboard/repairman/', views.repairman_dashboard, name='repairman_dashboard'),
    path('dashboard/seacraft/', views.seacraft_dashboard, name='seacraft_dashboard'),
    path('dashboard/logistics/', views.logistics_dashboard, name='logistics_dashboard'),
]