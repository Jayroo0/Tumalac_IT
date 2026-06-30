from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION 
from django.contrib.contenttypes.models import ContentType          
from .models import Vehicle, VehicleType, Driver  # 🟢 Added Driver model here
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


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

        # 🆕 ACTION D: PROCESSING INTERACTION FROM DRIVER DROPDOWN SET BUTTONS
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

    # Fetch values ensuring fast loading via select_related lookups
    vehicles = Vehicle.objects.all().select_related('vehicle_type', 'assigned_driver')
    types = VehicleType.objects.all()
    drivers = Driver.objects.filter(is_active=True) # 🟢 Context hook for dropdown lists
    
    context = {
        'vehicles': vehicles, 
        'types': types, 
        'drivers': drivers
    }
    return render(request, 'fleet/logistics_dashboard.html', context)

@csrf_exempt # 🛡️ Exempt from CSRF since this is an automated hardware scanner webhook
def rfid_sensor_trigger(request):
    """
    Automated Endpoint: Triggered by the physical gate sensor.
    Expects a POST request with JSON payload: {"rfid_tag": "TAG_VALUE_HERE"}
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST requests are accepted.'}, status=405)
    
    try:
        data = json.loads(request.body)
        tag_id = data.get('rfid_tag', '').strip()
        
        if not tag_id:
            return JsonResponse({'status': 'error', 'message': 'Missing rfid_tag identifier parameters.'}, status=400)
        
        # 🔍 Locate the asset mapped to this physical tag string
        vehicle = Vehicle.objects.filter(rfid_tag=tag_id).first()
        
        if not vehicle:
            return JsonResponse({'status': 'error', 'message': f'RFID Tag [{tag_id}] not matched to any fleet registry.'}, status=404)
        
        # 🛑 Guardrail rule: Block if it's undergoing critical repairs
        if vehicle.status == 'MAINTENANCE':
            return JsonResponse({
                'status': 'blocked', 
                'message': f"Automated deployment rejected: Asset '{vehicle.model_name}' is locked under MAINTENANCE constraints."
            }, status=403)
            
        # 🔄 Edge Case: If already deployed, don't repeat the save transaction logs
        if vehicle.status == 'DEPLOYED':
            return JsonResponse({'status': 'ignored', 'message': f"'{vehicle.model_name}' is already logged as DEPLOYED."}, status=200)
            
        # 🚀 Execute Automatic Status Shift Upgrades
        old_status = vehicle.status
        vehicle.status = 'DEPLOYED'
        vehicle.save()
        
        # Log to the admin records using a mock system user ID (e.g., user_id=1 or None)
        LogEntry.objects.create(
            user_id=1, # Default system account / fallback administrator ID
            content_type_id=ContentType.objects.get_for_model(vehicle).id,
            object_id=vehicle.id,
            object_repr=str(vehicle),
            action_flag=CHANGE,
            change_message=f"AUTOMATED RFID DEPLOYMENT: Scanned at external perimeter gate. Shifted from {old_status}."
        )
        
        return JsonResponse({
            'status': 'success', 
            'message': f"Asset unit '{vehicle.model_name}' automatically set to DEPLOYED out of premises.",
            'vehicle_id': vehicle.id,
            'plate_number': vehicle.plate_number
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data string format.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)