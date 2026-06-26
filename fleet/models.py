from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class VehicleType(models.Model):
    name = models.CharField(max_length=100) # e.g., Mobile Command Center, Motorcycle
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, default="fa-car", help_text="FontAwesome icon class")

    def __str__(self):
        return self.name

# fleet/models.py

class Vehicle(models.Model):
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('DEPLOYED', 'Deployed'),
        ('MAINTENANCE', 'Under Maintenance'),
    ]
    plate_number = models.CharField(max_length=20, unique=True)
    
    # FIX THIS LINE: Change 'on_ automakers' to 'on_delete'
    vehicle_type = models.ForeignKey(VehicleType, on_delete=models.CASCADE)
    
    model_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    assigned_driver = models.CharField(max_length=150, blank=True, null=True)

    def __str__(self):
        return f"{self.vehicle_type.name} - {self.plate_number}"

class Part(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    quantity = models.PositiveIntegerField(default=0)  # <-- ADD THIS FIELD

    def __str__(self):
        return f"{self.name} (Qty: {self.quantity})"

class MaintenanceRecord(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    part = models.ForeignKey(Part, on_delete=models.CASCADE)
    replaced_date = models.DateTimeField(default=timezone.now)
    next_due_date = models.DateTimeField(help_text="Varies based on part lifespan configuration")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.vehicle} - {self.part.name} replaced on {self.replaced_date.date()}"

class VehicleIssue(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Issue: {self.vehicle.plate_number} - {self.description[:30]}"

class DashboardNotification(models.Model):
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.message