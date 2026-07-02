from django.db import models

class VehicleType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Driver(models.Model):
    name = models.CharField(max_length=100, unique=True)
    license_number = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    # 🛠️ FIX: Corrected __clstr__ typo to the standardized magic method __str__
    def __str__(self):
        return self.name

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('OPERATIONAL', 'Operational'),
        ('MAINTENANCE', 'Maintenance'),
        ('DEPLOYED', 'Deployed'),
    ]

    model_name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE)
    
    # 🛠️ FIX: Added choices constraint to bind the field parameters safely to your options matrix
    status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='OPERATIONAL'
    )
    
    assigned_driver = models.ForeignKey(
        Driver, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='vehicles'
    )

    def __str__(self):
        return f"{self.model_name} ({self.plate_number})"