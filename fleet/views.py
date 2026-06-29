from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Vehicle, VehicleType

# =========================================================================
# 1. HOMEPAGE VIEW (With Automatic Domain Sorting Matrices)
# =========================================================================
def homepage(request):
    all_vehicles = Vehicle.objects.all().select_related('vehicle_type')
    
    # Automatic Category Segmentation Layer
    marine_crafts = all_vehicles.filter(vehicle_type__name__iexact='MARINE')
    land_vehicles = all_vehicles.exclude(vehicle_type__name__iexact='MARINE')
    
    context = {
        'marine_crafts': marine_crafts,
        'land_vehicles': land_vehicles,
        'total_count': all_vehicles.count(),
        'functioning_count': all_vehicles.filter(status='FUNCTIONING').count(),
        'maintenance_count': all_vehicles.filter(status='UNDER MAINTENANCE').count(),
        'broken_count': all_vehicles.filter(status='OUT OF ORDER').count(),
    }
    return render(request, 'fleet/homepage.html', context)


# =========================================================================
# 2. GENERAL REPAIRMAN DASHBOARD (Land/Global Transportation)
# =========================================================================
def repairman_dashboard(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        new_status = request.POST.get('status')
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        vehicle.status = new_status
        vehicle.save()
        messages.success(request, f"Status updated for {vehicle.model_name} successfully!")
        return redirect('repairman_dashboard')

    # Exclude marine vehicles so the repairman focuses only on land assets
    vehicles = Vehicle.objects.all().exclude(vehicle_type__name__iexact='MARINE').select_related('vehicle_type')
    return render(request, 'fleet/repairman_dashboard.html', {'vehicles': vehicles, 'title': 'Land Mobile Operations Portal'})


# =========================================================================
# 3. SPECIALIZED SEACRAFT DASHBOARD (Marine Crafts Only)
# =========================================================================
def seacraft_dashboard(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle_id')
        new_status = request.POST.get('status')
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        vehicle.status = new_status
        vehicle.save()
        messages.success(request, f"Maritime unit status updated successfully!")
        return redirect('seacraft_dashboard')

    # Filter down exclusively to marine vehicles
    vehicles = Vehicle.objects.filter(vehicle_type__name__iexact='MARINE').select_related('vehicle_type')
    
    # FIXED: Now correctly pointing to seacraft_dashboard.html template!
    return render(request, 'fleet/seacraft_dashboard.html', {'vehicles': vehicles, 'title': 'Maritime Division Seacraft Portal'})


# =========================================================================
# 4. LOGISTICS DASHBOARD (Onboarding & Driver Assignment Matrix)
# =========================================================================
def logistics_dashboard(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # Action Block A: Add Vehicle (Via our clean modal button popup)
        if action == 'add_vehicle':
            model_name = request.POST.get('model_name')
            plate_number = request.POST.get('plate_number')
            type_id = request.POST.get('vehicle_type')
            
            v_type = get_object_or_404(VehicleType, id=type_id)
            Vehicle.objects.create(model_name=model_name, plate_number=plate_number, vehicle_type=v_type)
            messages.success(request, f"Asset Row [{plate_number}] loaded into database registry index!")
            
        # Action Block B: Driver Manifest Assignment Routing Update
        elif action == 'assign_driver':
            vehicle_id = request.POST.get('vehicle_id')
            driver_name = request.POST.get('driver_name') or "None Assigned"
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle.assigned_driver = driver_name
            vehicle.save()
            messages.success(request, f"Driver manifest updated for {vehicle.model_name}.")
            
        return redirect('logistics_dashboard')

    vehicles = Vehicle.objects.all().select_related('vehicle_type')
    types = VehicleType.objects.all()
    return render(request, 'fleet/logistics_dashboard.html', {'vehicles': vehicles, 'types': types})