from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Vehicle, VehicleType
from django.contrib.auth import logout
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION # 👈 IMPORT LOG MODIFIERS
from django.contrib.contenttypes.models import ContentType          # 👈 IMPORT CONTENT TYPES

def custom_user_logout(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, "You have been logged out of the PDRRMO operations network.")
    return redirect('homepage')



# fleet/views.py

# 🆕 ADD THIS HELPER FUNCTION AT THE TOP OF YOUR FILE:
def check_user_role(user, group_name, keywords):
    """
    Helper function to securely evaluate if a user belongs to a specific group
    or has a profile keyword in their username.
    """
    if user.is_superuser:
        return True
    
    # Check database groups
    user_group_names = list(user.groups.values_list('name', flat=True))
    if group_name in user_group_names:
        return True
        
    # Check username keywords as a fail-safe
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
# 1. HOMEPAGE VIEW (With Automatic Domain Sorting Matrices)
# =========================================================================
def homepage(request):
    all_vehicles = Vehicle.objects.all().select_related('vehicle_type')
    marine_crafts = all_vehicles.filter(vehicle_type__name__iexact='MARINE')
    land_vehicles = all_vehicles.exclude(vehicle_type__name__iexact='MARINE')
    
    context = {
        'marine_crafts': marine_crafts,
        'land_vehicles': land_vehicles,
        'total_count': all_vehicles.count(),
        'operational_count': all_vehicles.filter(status='OPERATIONAL').count(),
        'maintenance_count': all_vehicles.filter(status='MAINTENANCE').count(),
        'deployed_count': all_vehicles.filter(status='DEPLOYED').count(),
    }
    return render(request, 'fleet/homepage.html', context)


# =========================================================================
# 2. CENTRAL ROUTER VIEW (The Single Portal Gateway)
# =========================================================================
# fleet/views.py

# fleet/views.py

@login_required
def dashboard_router(request):
    user = request.user
    username_lower = user.username.lower()

    # Get a clean list of all group names assigned to this user
    user_group_names = list(user.groups.values_list('name', flat=True))
    
    # 📝 TERMINAL DEBUGGER: This prints directly to your black console window 
    # so you can see why it's failing!
    print("\n--- PDRRMO DEBUGLOG PORTAL ---")
    print(f"Active User Logging In: {user.username}")
    print(f"Is Staff Status Flag: {user.is_staff}")
    print(f"Detected Database Groups: {user_group_names}")
    print("-------------------------------\n")

    # 1. Main System Administrator Gateway
    if user.is_superuser:
        return redirect('/admin/')

    # 2. Strict Database Group Matches
    if 'Seacraft' in user_group_names:
        return redirect('seacraft_dashboard')
    elif 'Repairman' in user_group_names:
        return redirect('repairman_dashboard')
    elif 'Logistics' in user_group_names:
        return redirect('logistics_dashboard')

    # 3. 🛡️ BULLETPROOF SAFETY NET: Username Profile Keyword Interception
    # If database groups are broken, this checks the account name itself!
    if 'sea' in username_lower or 'maritime' in username_lower:
        return redirect('seacraft_dashboard')
    elif 'tech' in username_lower or 'repair' in username_lower or 'mechanic' in username_lower:
        return redirect('repairman_dashboard')
    elif 'log' in username_lower or 'depot' in username_lower:
        return redirect('logistics_dashboard')

    # 4. Final Fallback for staff accounts without keywords or groups
    if user.is_staff:
        return redirect('logistics_dashboard')

    # Fallback if account has absolutely zero routing match parameters
    messages.warning(request, f"Profile '{user.username}' has no operational role assigned.")
    return redirect('homepage') 


# =========================================================================
# 3. GENERAL REPAIRMAN DASHBOARD (Land/Global Transportation)
# =========================================================================
@login_required
def repairman_dashboard(request):
    user = request.user
    username_lower = user.username.lower()
    user_group_names = list(user.groups.values_list('name', flat=True))

    # 🛡️ Updated Guardrail: Pass if Admin, in Group, OR has the keyword in username
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
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        old_status = vehicle.status
        new_status = request.POST.get('status')
        
        vehicle.status = new_status
        vehicle.save()
        
        log_action_to_admin(request, vehicle, CHANGE, f"Changed status from {old_status} to {new_status} via Repair Bench.")
        messages.success(request, f"Status updated for {vehicle.model_name} successfully!")
        return redirect('repairman_dashboard')

    vehicles = Vehicle.objects.all().exclude(vehicle_type__name__iexact='MARINE').select_related('vehicle_type')
    return render(request, 'fleet/repairman_dashboard.html', {'vehicles': vehicles})


# =========================================================================
# 4. SPECIALIZED SEACRAFT DASHBOARD (Marine Crafts Only)
# =========================================================================
# Inside fleet/views.py

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
        # 🔄 FIX: Check for both common template variable names just in case
        vehicle_id = request.POST.get('vehicle_id') or request.POST.get('craft_id')
        new_status = request.POST.get('status')

        print(f"\n--- SEACRAFT STATUS UPDATE DEBUG ---")
        print(f"Received Vehicle ID: {vehicle_id}")
        print(f"Received Raw Status: {new_status}")
        print(f"------------------------------------\n")

        if vehicle_id and new_status:
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            old_status = vehicle.status
            
            # Clean and match validation choices format (forced uppercase)
            cleaned_status = str(new_status).strip().upper()
            
            vehicle.status = cleaned_status
            vehicle.save()
            
            log_action_to_admin(request, vehicle, CHANGE, f"Changed maritime status from {old_status} to {cleaned_status} via Maritime System.")
            messages.success(request, f"Maritime unit [{vehicle.plate_number}] status updated to {cleaned_status} successfully!")
        else:
            messages.error(request, "Failed to update status: Missing asset identifier parameters.")

        return redirect('seacraft_dashboard')

    vehicles = Vehicle.objects.filter(vehicle_type__name__iexact='MARINE').select_related('vehicle_type')
    return render(request, 'fleet/seacraft_dashboard.html', {'vehicles': vehicles})

# =========================================================================
# 5. LOGISTICS DASHBOARD (Onboarding & Driver Assignment Matrix)
# =========================================================================
@login_required
def logistics_dashboard(request):

    user = request.user

    # 🛡️ Clean authorization check using the helper function
    # Staff accounts also get access to logistics by default
    if not (user.is_staff or check_user_role(user, 'Logistics', ['log', 'depot'])):
        messages.error(request, "Access restricted to Logistics Depot management accounts.")
        return redirect('homepage')


    # Pass if Admin, Logistics group/keywords, OR is basic staff user
    is_logistics_staff = (
        check_user_role(request.user, 'Logistics', ['log', 'depot']) or 
        request.user.is_staff
    )
    
    if not is_logistics_staff:
        messages.error(request, "Access restricted to Logistics Depot management accounts.")
        return redirect('homepage')

    # Inside fleet/views.py -> def logistics_dashboard(request):

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_vehicle':
            # ... (keep existing code) ...
            pass
            
        elif action == 'assign_driver':
            # ... (keep existing code) ...
            pass

        elif action == 'deploy_vehicle':
            # ... (keep existing code) ...
            pass

        # 🆕 NEW RETURN FEATURE: Bring asset back from deployment field
        elif action == 'return_vehicle':
            vehicle_id = request.POST.get('vehicle_id')
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            
            old_status = vehicle.status
            vehicle.status = 'OPERATIONAL'  # Revert status back to active depot pool
            vehicle.save()
            
            log_action_to_admin(request, vehicle, CHANGE, f"Returned asset to logistics hub depot from field deployment.")
            messages.success(request, f"Asset unit {vehicle.model_name} has returned to base and is available for assignment.")
            
        return redirect('logistics_dashboard')

    vehicles = Vehicle.objects.all().select_related('vehicle_type')
    types = VehicleType.objects.all()
    return render(request, 'fleet/logistics_dashboard.html', {'vehicles': vehicles, 'types': types})
