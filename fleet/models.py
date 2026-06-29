from django.db import models
from django.contrib.auth.models import User

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True) # e.g., "MARINE", "MOTORCYCLE", "TRUCK"

    def __str__(self):
        return self.name

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('FUNCTIONING', '⚙️ Functioning'),
        ('UNDER MAINTENANCE', '🔧 Under Maintenance'),
        ('OUT OF ORDER', '🚨 Out of Order'),
    ]

    model_name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE, related_name='vehicles')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='FUNCTIONING')
    assigned_driver = models.CharField(max_length=100, blank=True, null=True, default="None Assigned")

    def __str__(self):
        return f"{self.model_name} [{self.plate_number}]"
    
