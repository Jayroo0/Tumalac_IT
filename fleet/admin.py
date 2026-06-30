from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.admin.models import LogEntry
from django.contrib import messages
from .models import Vehicle, VehicleType, Driver  # 🟢 Added Driver model here

# =========================================================================
# 1. ADMIN HEADERS PANEL STYLING TWEAKS
# =========================================================================
admin.site.site_header = "PDRRMO Fleet Control HQ Admin"
admin.site.site_title = "PDRRMO Portal"
admin.site.index_title = "Command & Control Configuration Center"


# =========================================================================
# 2. READ-ONLY ACTIONS AUDIT LOG VIEW
# =========================================================================
@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag')
    list_filter = ('action_time', 'user', 'action_flag')
    search_fields = ('object_repr', 'change_message')
    
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


# =========================================================================
# 3. VEHICLE TYPE CONFIGURATION
# =========================================================================
@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)


# =========================================================================
# 4. NEW: DRIVER MODEL REGISTRATION
# =========================================================================
@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'license_number', 'phone_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'license_number', 'phone_number')


# =========================================================================
# 5. VEHICLE CONFIGURATION WITH STYLING INJECTIONS (CLEANED)
# =========================================================================
@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'model_name', 
        'plate_number', 
        'vehicle_type', 
        'status', 
        'driver_phone'  # 🔍 Pulls from the custom display method below
    ]
    list_filter = ('status', 'vehicle_type')
    # 🔄 Note: we use assigned_driver__name because assigned_driver is now a model reference
    search_fields = ('model_name', 'plate_number', 'assigned_driver__name')

    @admin.display(description="Driver Phone Number")
    def driver_phone(self, obj):
        """
        Safely reaches through the foreign key relationship to grab 
        the assigned operator's phone number from the Driver database table.
        """
        if obj.assigned_driver and obj.assigned_driver.phone_number:
            return obj.assigned_driver.phone_number
        return "-"


# =========================================================================
# 6. USER ACCOUNTS ACTIONS SYSTEM CONTROL
# =========================================================================
@admin.action(description="🔒 Deactivate selected user accounts")
def deactivate_users(modeladmin, request, queryset):
    queryset.update(is_active=False)
    modeladmin.message_user(request, "Selected accounts have been cleanly deactivated.", messages.SUCCESS)

@admin.action(description="🔓 Activate selected user accounts")
def activate_users(modeladmin, request, queryset):
    queryset.update(is_active=True)
    modeladmin.message_user(request, "Selected accounts have been reactivated.", messages.SUCCESS)

# Safely swap default User registration for our custom actionable layout
admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(DefaultUserAdmin):
    actions = [deactivate_users, activate_users]