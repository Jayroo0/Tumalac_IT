from django.db import models

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

# fleet/models.py

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('OPERATIONAL', 'Operational'),
        ('MAINTENANCE', 'Maintenance'),
        ('DEPLOYED', 'Deployed'),
    ]

    model_name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.ForeignKey('VehicleType', on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPERATIONAL')
    assigned_driver = models.CharField(max_length=100, default='None Assigned')
    # 🆕 Added contact field for explicit mobile dialing
    driver_phone = models.CharField(max_length=20, default='', blank=True, help_text="e.g., +639123456789")

    def __str__(self):
        return f"{self.model_name} ({self.plate_number})"