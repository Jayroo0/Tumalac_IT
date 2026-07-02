from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout,authenticate, login
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION 
from django.contrib.contenttypes.models import ContentType          
from django.db.models import Case, When, Value, IntegerField
from .models import Vehicle, VehicleType, Driver

# =========================================================================
# SYSTEM SECURITY & AUDIT LOG HELPERS
# =========================================================================
# fleet/views.py

def login_view(request):
    # Your view logic here
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(username=username, password=password)
    
    if user is not None:
       login(request, user)
            # FIX HERE: Redirect using the namespace:name format
       return redirect('dashboard_portal:dashboard_portal') 
    else:
            # Handle invalid login credentials
            pass
    
    return render(request, 'fleet/login.html')


def custom_user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out of the PDRRMO operations network.")
    return redirect('dashboard_portal:login')

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

    # ==========================================
    # STEP 1: RESOLVE BY EXPLICIT GROUP DESIGNATION
    # ==========================================
    group_routing_matrix = {
        'Seacraft Dispatch': 'dashboard_portal:seacraft_dispatch',
        'Logistics Managers': 'dashboard_portal:logistics_dashboard',
        'Logistics':          'dashboard_portal:logistics_dashboard',
        'Repairman':          'dashboard_portal:repairman_dashboard',
        'Seacraft':           'dashboard_portal:seacraft_dashboard',
        
        # 🌟 ADMINS: Any group named exactly like below will map directly
        'Incident Commander': 'dashboard_portal:command_center', 
    }

    # Evaluate matches securely based on group priority
    for group_name, destination_url in group_routing_matrix.items():
        if group_name in user_group_names:
            return redirect(destination_url)

    # ==========================================
    # STEP 2: FALLBACK STRATEGY BY USERNAME MATCH
    # ==========================================
    if 'sea' in username_lower or 'maritime' in username_lower:
        return redirect('dashboard_portal:seacraft_dashboard')
    elif 'tech' in username_lower or 'repair' in username_lower or 'mechanic' in username_lower:
        return redirect('dashboard_portal:repairman_dashboard')
    elif 'log' in username_lower or 'depot' in username_lower:
        return redirect('dashboard_portal:logistics_dashboard')
    
    print(f"User {user.username} has no designated functional group. Rendering process standby state.")
    return render(request, 'fleet/unassigned_pending.html')


    # ==========================================
    # STEP 3: SAFEST UNMAPPED ACCOUNT ESCAPE VALVE
    # ==========================================
    # If a custom group was added but not explicitly added to code matrix yet,
    # don't lock them out. Route them safely to the basic general homepage view.
    messages.info(request, f"Welcome {user.username}. Accessing general operations feed.")
    return redirect('dashboard_portal:homepage') 


# =========================================================================
# 3. GENERAL REPAIRMAN DASHBOARD (Land / Tech Fleet)
# =========================================================================
@login_required
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

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        action_type = request.POST.get('action_type', 'STATUS_TOGGLE') # Fallback default to keep compatibility
        
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            
            # ♻️ HANDLE DISPOSAL ACTION TYPE FLAG (WITH REMARKS VALIDATION)
            if action_type == 'FLAG_DISPOSAL':
                remarks = request.POST.get('disposal_remarks', '').strip()
                
                if not remarks:
                    messages.error(request, f"Failure: You must provide a maintenance justification remark to flag {vehicle.model_name} for disposal.")
                    return redirect('dashboard_portal:repairman_dashboard')

                vehicle.status = 'PENDING_DISPOSAL'
                if vehicle.assigned_driver:
                    vehicle.assigned_driver = None  # Force detach operators
                vehicle.save()
                
                # Log to system audit trail trailing the repairman's specific remarks
                log_action_to_admin(request, vehicle, CHANGE, f"Flagged asset {vehicle.model_name} for disposal from repair workshop. Remarks: {remarks}")
                messages.warning(request, f"{vehicle.model_name} has been routed to Logistics for decommissioning evaluation.")
            
            # STANDARD TOGGLE SWITCH PIPELINE
            else:
                new_status = request.POST.get('status')
                if new_status:
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
                    
            return redirect('dashboard_portal:repairman_dashboard')

    # FIX: Fused the query layout so priority sorting is no longer overwritten
    vehicles = Vehicle.objects.exclude(
        vehicle_type__name__iexact='MARINE'
    ).select_related(
        'vehicle_type', 'assigned_driver'
    ).order_by(
        Case(
            When(status='MAINTENANCE', then=Value(1)),
            When(status='OPERATIONAL', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
        'model_name'
    )
    
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
        vehicle_id = request.POST.get('vehicle_id')
        action_type = request.POST.get('action_type', 'STATUS_TOGGLE') # Fallback default
        
        if vehicle_id:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            
            # ♻️ HANDLE DISPOSAL ACTION TYPE FLAG (WITH REMARKS VALIDATION)
            if action_type == 'FLAG_DISPOSAL':
                remarks = request.POST.get('disposal_remarks', '').strip()
                
                if not remarks:
                    messages.error(request, f"Failure: You must provide a justification remark to flag {vehicle.model_name} for disposal.")
                    return redirect('dashboard_portal:seacraft_dashboard')

                vehicle.status = 'PENDING_DISPOSAL'
                if vehicle.assigned_driver:
                    vehicle.assigned_driver = None  # Force detach operators
                vehicle.save()
                
                # Appends operator remarks directly into your existing administrative audit trail function
                log_action_to_admin(request, vehicle, CHANGE, f"Flagged maritime asset {vehicle.model_name} for disposal processing. Remarks: {remarks}")
                messages.warning(request, f"{vehicle.model_name} has been routed to Logistics for disposal confirmation.")
            
            # STANDARD TOGGLE SWITCH PIPELINE
            else:
                new_status = request.POST.get('status')
                if new_status in ['OPERATIONAL', 'MAINTENANCE']:
                    if new_status == 'MAINTENANCE' and vehicle.assigned_driver:
                        vehicle.assigned_driver = None
                    
                    old_status = vehicle.status
                    vehicle.status = new_status
                    vehicle.save()
                    messages.success(request, f"Status for {vehicle.model_name} updated successfully.")
            
            return redirect('dashboard_portal:seacraft_dashboard')

    # GET LOGIC: Exclude archived and pending disposal assets from regular active visibility arrays
    vehicles = Vehicle.objects.filter(
        vehicle_type__name__iexact='MARINE'
    ).exclude(
        status__in=['PENDING_DISPOSAL', 'ARCHIVED', 'DISPOSED']
    ).select_related(
        'vehicle_type', 'assigned_driver'
    ).order_by(
        Case(
            When(status='MAINTENANCE', then=Value(1)),
            When(status='OPERATIONAL', then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        ),
        'model_name'
    )
    return render(request, 'fleet/seacraft_dashboard.html', {'vehicles': vehicles})
# =========================================================================
# 5. LOGISTICS DASHBOARD (Onboarding & Driver Assignment Matrix)
# =========================================================================
@login_required
def logistics_dashboard(request):
    user = request.user

    if not (user.is_staff or check_user_role(user, 'Logistics', ['log', 'depot'])):
        messages.error(request, "Access restricted to Logistics Depot management accounts.")
        return redirect('homepage')

    # 1. Find IDs of drivers currently out on the field in a deployed vehicle
    deployed_driver_ids = Vehicle.objects.filter(
        status='DEPLOYED', 
        assigned_driver__isnull=False
    ).values_list('assigned_driver_id', flat=True)

    # 2. Fetch drivers: Include them ONLY if they are active AND not busy.
    available_drivers = Driver.objects.filter(is_active=True).exclude(id__in=deployed_driver_ids)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        vehicle_id = request.POST.get('vehicle_id')

        # Check if this POST request came from the onboarding modal fallback form
        if 'asset_name' in request.POST:
            asset_name = request.POST.get('asset_name')
            asset_type = request.POST.get('asset_type')
            # ... custom fallback creation logic can go here if needed ...
            return redirect('dashboard_portal:logistics_dashboard')

        # ACTION A: DEPLOY VEHICLE OUTBOUND
        if action == 'deploy_vehicle':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            if vehicle.status.upper() == 'MAINTENANCE':
                messages.error(request, f"⚠️ CRITICAL BLOCK: '{vehicle.model_name}' is logged under MAINTENANCE.")
                return redirect('dashboard_portal:logistics_dashboard')
            
            vehicle.status = 'DEPLOYED'
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, "Deployed asset unit to active emergency route.")
            messages.success(request, f"Asset unit {vehicle.model_name} deployed successfully!")
            return redirect('dashboard_portal:logistics_dashboard')

        # ACTION B: RETURN VEHICLE TO DEPOT BASE
        elif action == 'return_vehicle':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle.status = 'OPERATIONAL'
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, "Returned asset unit back to operational depot storage.")
            messages.success(request, f"Asset unit {vehicle.model_name} returned to depot!")
            return redirect('dashboard_portal:logistics_dashboard')

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
            return redirect('dashboard_portal:logistics_dashboard')

        # ACTION D: PROCESSING INTERACTION FROM DRIVER DROPDOWN SET BUTTONS
        elif action == 'set_driver':
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            driver_id = request.POST.get('driver_id')
            
            if driver_id:  
                driver_obj = get_object_or_404(Driver, id=driver_id)
                vehicle.assigned_driver = driver_obj
                msg = f"Assigned operator {driver_obj.name} to {vehicle.model_name}."
            else:  
                vehicle.assigned_driver = None
                msg = f"Removed driver assignment from asset {vehicle.model_name}."
                
            vehicle.save()
            log_action_to_admin(request, vehicle, CHANGE, msg)
            messages.success(request, msg)
            return redirect('dashboard_portal:logistics_dashboard')

        # ACTION E: CONFIRM DISPOSAL PIPELINE
        elif action == 'confirm_disposal':
            vessel_to_archive = get_object_or_404(Vehicle, id=vehicle_id)
            vessel_to_archive.status = 'ARCHIVED'
            if hasattr(vessel_to_archive, 'is_active'):
                vessel_to_archive.is_active = False
            vessel_to_archive.save()
            log_action_to_admin(request, vessel_to_archive, CHANGE, f"Approved and permanently archived asset: {vessel_to_archive.model_name}")
            messages.success(request, f"Asset {vessel_to_archive.model_name} successfully moved to secure archives.")
            return redirect('dashboard_portal:logistics_dashboard')

        # ACTION F: DECLINE DISPOSAL PIPELINE
        elif action == 'decline_disposal':
            vessel_to_repair = get_object_or_404(Vehicle, id=vehicle_id)
            vessel_to_repair.status = 'MAINTENANCE'
            vessel_to_repair.save()
            log_action_to_admin(request, vessel_to_repair, CHANGE, f"Rejected disposal request. Returned to maintenance array: {vessel_to_repair.model_name}")
            messages.info(request, f"Disposal declined. {vessel_to_repair.model_name} reverted to MAINTENANCE status.")
            return redirect('dashboard_portal:logistics_dashboard')

    # =========================================================================
    # 🔄 GET WORKFLOW: SPLIT DATA INTO CHANNELS
    # =========================================================================
    all_vehicles = Vehicle.objects.all().select_related('vehicle_type', 'assigned_driver')
    
    land_vehicles = all_vehicles.exclude(vehicle_type__name__iexact='MARINE').exclude(status='ARCHIVED')
    sea_crafts = all_vehicles.filter(vehicle_type__name__iexact='MARINE').exclude(status='ARCHIVED')
    pending_disposals = all_vehicles.filter(status='PENDING_DISPOSAL')
    
    types = VehicleType.objects.all()
    
    context = {
        'land_vehicles': land_vehicles, 
        'sea_crafts': sea_crafts, 
        'types': types, 
        'drivers': available_drivers,
        'pending_disposals': pending_disposals,
    }
    return render(request, 'fleet/logistics_dashboard.html', context)

@login_required
def seacraft_dispatch_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        vehicle_id = request.POST.get('vehicle_id')
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)

        # Handle Operator Assignment
        if action == 'set_driver':
            driver_id = request.POST.get('driver_id')
            if driver_id:
                driver = get_object_or_404(Driver, id=driver_id)
                vehicle.assigned_driver = driver
            else:
                vehicle.assigned_driver = None # Unassigned / Standby
            vehicle.save()

        # Handle Deploy Trigger Action
        elif action == 'deploy_vehicle':
            vehicle.status = 'DEPLOYED'
            vehicle.save()

        # Handle Return Trigger Action
        elif action == 'return_vehicle':
            vehicle.status = 'OPERATIONAL'
            vehicle.save()

        # Always redirect back to reload the dashboard cleanly
        return redirect('dashboard_portal:seacraft_dispatch')

    # 📤 2. RENDER THE DASHBOARD LAYOUT (GET Request)
    sea_crafts = Vehicle.objects.filter(vehicle_type__name='MARITIME')
    drivers = Driver.objects.filter(is_active=True) # Adjust criteria as needed
    
    return render(request, 'fleet/seacraft_dispatch.html', {
        'sea_crafts': sea_crafts,
        'drivers': drivers
    })
