from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION 
from django.contrib.contenttypes.models import ContentType          
from django.db.models import Case, When, Value, IntegerField
from .models import Vehicle, VehicleType, Driver  # 🟢 Added Driver model here

# =========================================================================
# SYSTEM SECURITY & AUDIT LOG HELPERS
# =========================================================================
def custom_user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out of the PDRRMO operations network.")
    return redirect('homepage')

def check_user_role(user, group_name, keywords):
    """
    Helper function to securely evaluate if a user belongs to a specific group
    or has a profile keyword in their username.
    """
    if user.is_superuser:
        return True
    
    user_group_names = list(user.groups.values_list('name', flat=True))
    if group_name in user_group_names:
        return True
        
    username_lower = user.username.lower()
    if any(kw in username_lower for kw in keywords):
        return True
        
    return False

def log_action_to_admin(request, object_instance, action_flag, change_message):
    LogEntry.objects.create(
        user_id=request.user.id,
        content_type_id=ContentType.objects.get_for_model(object_instance).id,
        object_id=object_instance.id,
        object_repr=str(object_instance),
        action_flag=action_flag,
        change_message=change_message
    )


# =========================================================================
# 1. HOMEPAGE VIEW
# =========================================================================
def homepage(request):
    all_vehicles = Vehicle.objects.all().select_related('vehicle_type', 'assigned_driver')
    sea_crafts = all_vehicles.filter(vehicle_type__name__iexact='MARINE')
    land_vehicles = all_vehicles.exclude(vehicle_type__name__iexact='MARINE')
    total_fleet = Vehicle.objects.exclude(status='disposal').count()
    land_operational_count = land_vehicles.filter(status='OPERATIONAL').count()
    sea_operational_count = sea_crafts.filter(status='OPERATIONAL').count()
    land_deployed_count = land_vehicles.filter(status='DEPLOYED').count()
    sea_deployed_count = sea_crafts.filter(status='DEPLOYED').count()
    land_maintenance_count = land_vehicles.filter(status='MAINTENANCE').count()
    sea_maintenance_count = sea_crafts.filter(status='MAINTENANCE').count()

    context = {
        'total_fleet': total_fleet,
        'sea_crafts': sea_crafts,
        'land_vehicles': land_vehicles,
        'land_operational_count': land_operational_count,
        'sea_operational_count': sea_operational_count,
        'land_deployed_count': land_deployed_count,
        'sea_deployed_count': sea_deployed_count,
        'land_maintenance_count': land_maintenance_count,
        'sea_maintenance_count': sea_maintenance_count,
        'total_count': all_vehicles.count(),
        'operational_count': all_vehicles.filter(status='OPERATIONAL').count(),
        'maintenance_count': all_vehicles.filter(status='MAINTENANCE').count(),
        'deployed_count': all_vehicles.filter(status='DEPLOYED').count(),
    }
    return render(request, 'fleet/homepage.html', context)


# =========================================================================
# 2. CENTRAL ROUTER VIEW (The Single Portal Gateway)
# =========================================================================
@login_required
def dashboard_router(request):
    user = request.user
    username_lower = user.username.lower()
    user_group_names = list(user.groups.values_list('name', flat=True))
    
    print("\n--- PDRRMO DEBUGLOG PORTAL ---")
    print(f"Active User Logging In: {user.username}")
    print(f"Is Staff Status Flag: {user.is_staff}")
    print(f"Detected Database Groups: {user_group_names}")
    print("-------------------------------\n")

    if user.is_superuser:
        return redirect('/admin/')

    if 'Seacraft' in user_group_names:
        return redirect('seacraft_dashboard')
    elif 'Repairman' in user_group_names:
        return redirect('repairman_dashboard')
    elif 'Logistics' in user_group_names:
        return redirect('logistics_dashboard')

    if 'sea' in username_lower or 'maritime' in username_lower:
        return redirect('seacraft_dashboard')
    elif 'tech' in username_lower or 'repair' in username_lower or 'mechanic' in username_lower:
        return redirect('repairman_dashboard')
    elif 'log' in username_lower or 'depot' in username_lower:
        return redirect('logistics_dashboard')

    if user.is_staff:
        return redirect('logistics_dashboard')

    messages.warning(request, f"Profile '{user.username}' has no operational role assigned.")
    return redirect('homepage') 


# =========================================================================
# 3. GENERAL REPAIRMAN DASHBOARD (Land / Tech Fleet)
# =========================================================================
@login_required
def repairman_dashboard(request):
    user = request.user
    username_lower = user.username.lower()
    user_group_names = list(user.groups.values_list('name', flat=True))

    is_authorized = (
        user.is_superuser or 
        'Repairman' in user_group_names or 
        'tech' in username_lower or 'repair' in username_lower or 'mechanic' in username_lower
    )
    
    if not is_authorized:
        messages.error(request, "Access restricted to authorized Repair Technicians.")
        return redirect('homepage')

    # Line 124
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        new_status = request.POST.get('status')
        
        if vehicle_id and new_status:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            
            if new_status in ['OPERATIONAL', 'MAINTENANCE']:
                if new_status == 'MAINTENANCE' and vehicle.assigned_driver:
                    vehicle.assigned_driver = None
                
                vehicle.status = new_status
                vehicle.save()
                messages.success(request, f"Status for {vehicle.model_name} updated successfully.")
            else:
                messages.error(request, "Unauthorized status change attempted.")
        else:
            messages.error(request, "Missing structural data parameters.")
            
        return redirect('repairman_dashboard')

    # 2. Render Page Grid with Custom Priority Sorting (GET requests)
    # This creates a virtual sorting weights layer: Maintenance = 1, Operational = 2, Deployed = 3
    vehicles = Vehicle.objects.all().order_by(
        Case(
            When(status='MAINTENANCE', then=Value(1)),
            When(status='OPERATIONAL', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
        'model_name' # Secondary sorting alphabetic by name if statuses are equal
    )

    vehicles = Vehicle.objects.all().exclude(vehicle_type__name__iexact='MARINE').select_related('vehicle_type', 'assigned_driver')
    return render(request, 'fleet/repairman_dashboard.html', {'vehicles': vehicles})


# =========================================================================
# 4. SPECIALIZED SEACRAFT DASHBOARD (Marine Crafts Only)
# =========================================================================
@login_required
def seacraft_dashboard(request):
    user = request.user
    username_lower = user.username.lower()
    user_group_names = list(user.groups.values_list('name', flat=True))

    is_authorized = (
        user.is_superuser or 
        'Seacraft' in user_group_names or 
        'sea' in username_lower or 'maritime' in username_lower
    )

    if not is_authorized:
        messages.error(request, "Access restricted to authorized Maritime Operators.")
        return redirect('homepage')

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id') or request.POST.get('craft_id')
        new_status = request.POST.get('status')

        if vehicle_id and new_status:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            old_status = vehicle.status
            cleaned_status = str(new_status).strip().upper()
            
            vehicle.status = cleaned_status
            vehicle.save()
            
            log_action_to_admin(request, vehicle, CHANGE, f"Changed maritime status from {old_status} to {cleaned_status} via Maritime System.")
            messages.success(request, f"Maritime unit [{vehicle.plate_number}] status updated to {cleaned_status} successfully!")
        else:
            messages.error(request, "Failed to update status: Missing asset identifier parameters.")

        return redirect('seacraft_dashboard')

    vehicles = Vehicle.objects.filter(vehicle_type__name__iexact='MARINE').select_related('vehicle_type', 'assigned_driver')
    return render(request, 'fleet/seacraft_dashboard.html', {'vehicles': vehicles})


# =========================================================================
# 5. LOGISTICS DASHBOARD (Onboarding & Driver Assignment Matrix)
# =========================================================================
@login_required
def logistics_dashboard(request):
    user = request.user

    # 1. Find IDs of drivers currently out on the field in a deployed vehicle
    deployed_driver_ids = Vehicle.objects.filter(
        status='DEPLOYED', 
        assigned_driver__isnull=False
    ).values_list('assigned_driver_id', flat=True)

    # 2. Fetch drivers: Include them ONLY if they are active AND not busy.
    available_drivers = Driver.objects.filter(is_active=True).exclude(id__in=deployed_driver_ids)
    
    # 🛡️ Cleaned up single unified authorization gate
    if not (user.is_staff or check_user_role(user, 'Logistics', ['log', 'depot'])):
        messages.error(request, "Access restricted to Logistics Depot management accounts.")
        return redirect('homepage')

    if request.method == 'POST':
        action = request.POST.get('action')
        vehicle_id = request.POST.get('vehicle_id')

        # ACTION A: DEPLOY VEHICLE OUTBOUND
        if action == 'deploy_vehicle':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            if vehicle.status.upper() == 'MAINTENANCE':
                messages.error(request, f"⚠️ CRITICAL BLOCK: '{vehicle.model_name}' is logged under MAINTENANCE.")
                return redirect('logistics_dashboard')
            
            vehicle.status = 'DEPLOYED'
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, "Deployed asset unit to active emergency route.")
            messages.success(request, f"Asset unit {vehicle.model_name} deployed successfully!")
            return redirect('logistics_dashboard')

        # ACTION B: RETURN VEHICLE TO DEPOT BASE
        elif action == 'return_vehicle':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle.status = 'OPERATIONAL'
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, "Returned asset unit back to operational depot storage.")
            messages.success(request, f"Asset unit {vehicle.model_name} returned to depot!")
            return redirect('logistics_dashboard')

        # ACTION C: NEW ASSET REGISTRATION ONBOARDING
        elif action == 'add_vehicle':
            model_name = request.POST.get('model_name')
            plate_number = request.POST.get('plate_number')
            type_id = request.POST.get('vehicle_type')
            
            v_type = get_object_or_404(VehicleType, id=type_id)
            new_asset = Vehicle.objects.create(
                model_name=model_name,
                plate_number=plate_number,
                vehicle_type=v_type,
                status='OPERATIONAL'
            )
            log_action_to_admin(request, new_asset, ADDITION, f"Registered new asset unit '{model_name}' into inventory records.")
            messages.success(request, f"New fleet asset '{model_name}' has been securely registered to the base depot map.")
            return redirect('logistics_dashboard')

        # ACTION D: PROCESSING INTERACTION FROM DRIVER DROPDOWN SET BUTTONS
        elif action == 'set_driver':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            driver_id = request.POST.get('driver_id')
            
            if driver_id:  # If an operator ID was chosen in the dropdown list
                driver_obj = get_object_or_404(Driver, id=driver_id)
                vehicle.assigned_driver = driver_obj
                msg = f"Assigned operator {driver_obj.name} to {vehicle.model_name}."
            else:  # "None" / Unassigned chosen
                vehicle.assigned_driver = None
                msg = f"Removed driver assignment from asset {vehicle.model_name}."
                
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, msg)
            messages.success(request, msg)
            return redirect('logistics_dashboard')

    # =========================================================================
    # 🔄 UPDATED GET WORKFLOW: SPLIT DATA INTO CHANNELS
    # =========================================================================
    # Optimization: Pull all records using single SQL join lookup query
    all_vehicles = Vehicle.objects.all().select_related('vehicle_type', 'assigned_driver')
    
    # Filter segments matching the exact type keys used by your dashboard template panels
    land_vehicles = all_vehicles.filter(vehicle_type__name__iexact='LAND')
    sea_crafts = all_vehicles.filter(vehicle_type__name__iexact='MARINE')
    
    types = VehicleType.objects.all()
    
    context = {
        'land_vehicles': land_vehicles, 
        'sea_crafts': sea_crafts, 
        'types': types, 
        'drivers': available_drivers, # Extracted from the deployed check above
    }
    return render(request, 'fleet/logistics_dashboard.html', context)