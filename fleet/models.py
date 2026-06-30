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

    def __clstr__(self):
        return self.name

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('OPERATIONAL', 'Operational'),
        ('MAINTENANCE', 'Maintenance'),
        ('DEPLOYED', 'Deployed'),
    ]

    # 🆕 Add this field for the physical sensor sync:
    rfid_tag = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Unique RFID tag identifier attached to the vehicle chassis.")

    model_name = models.CharField(max_length=100)
    plate_number = models.CharField(max_length=50, unique=True)
    vehicle_type = models.ForeignKey('VehicleType', on_delete=models.CASCADE)
    status = models.CharField(max_length=50, default='OPERATIONAL') # OPERATIONAL, MAINTENANCE, DEPLOYED
    
    # Change this from a CharField to a ForeignKey pointing to our new Driver model
    assigned_driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicles')

    def __str__(self):
        return f"{self.model_name} ({self.plate_number})"