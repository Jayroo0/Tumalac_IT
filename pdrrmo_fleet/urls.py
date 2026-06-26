# pdrrmo_fleet/pdrrmo_fleet/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # This automatically forwards root traffic directly to your fleet app's urls.py
    path('', include('fleet.urls')), 
]