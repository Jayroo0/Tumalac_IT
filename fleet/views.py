from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .models import VehicleType, Vehicle, Part, VehicleIssue, DashboardNotification
# Add to fleet/views.py
from django.contrib import messages # Optional: for low stock warnings

# fleet/views.py
from django.shortcuts import render
from .models import Vehicle, VehicleIssue

def homepage(request):
    """
    Renders the public-facing interactive status dashboard
    and loads all database fleet elements into context.
    """
    # 1. Fetch EVERYTHING from the database
    all_vehicles = Vehicle.objects.all().order_by('model_name')
    unresolved_issues = VehicleIssue.objects.filter(is_resolved=False).count()
    
    # 2. Package it up into the context dictionary
    context = {
        'vehicles': all_vehicles,          # This MUST match the {% for vehicle in vehicles %} loop in HTML!
        'active_issues_count': unresolved_issues,
    }
    
    # 3. Render out to the template
    return render(request, 'fleet/homepage.html', context)


def custom_logout(request):
    logout(request)
    return redirect('homepage')

def dashboard_redirect(request):
    if request.user.groups.filter(name__in=['Admin', 'Logistic']).exists():
        return redirect('admin_logistic_dashboard')
    elif request.user.groups.filter(name='Repairman').exists():
        return redirect('repairman_dashboard')
    return redirect('homepage')

# fleet/views.py

# fleet/views.py


# fleet/views.py

@login_required
def admin_logistic_dashboard(request):
    """
    Logistics Panel: Default table view tracking asset assignments 
    and parts ledger stock optimization controls.
    """
    # Handle incoming POST updates from the interactive matrix buttons
    if request.method == 'POST':
        # Operation A: Deploy Driver to Vehicle Asset
        if 'vehicle_id' in request.POST:
            vehicle_id = request.POST.get('vehicle_id')
            driver_name = request.POST.get('driver', '').strip()
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle.assigned_driver = driver_name
            vehicle.save()
            return redirect('admin_logistic_dashboard')
            
        # Operation B: Adjust Quantity Stock Counts Inline (+/-)
        elif 'part_id' in request.POST and 'adjust_stock' in request.POST:
            part_id = request.POST.get('part_id')
            action = request.POST.get('adjust_stock')
            part = get_object_or_404(Part, id=part_id)
            
            if action == 'up':
                part.quantity += 1
            elif action == 'down' and part.quantity > 0:
                part.quantity -= 1
                
            part.save()
            return redirect('admin_logistic_dashboard')

    # Read operations for loading view data arrays
    parts_list = Part.objects.all().order_by('name')
    
    # Bucket sorting elements explicitly for structural navigation tabs
    categorized_parts = {
        'Engine': [],
        'Tires': [],
        'Electrical': [],
        'General': []
    }
    
    for p in parts_list:
        name_lower = p.name.lower()
        desc_lower = p.description.lower()
        
        if 'tire' in name_lower or 'radial' in name_lower or 'wheel' in name_lower:
            categorized_parts['Tires'].append(p)
        elif 'engine' in desc_lower or 'alternator' in name_lower or 'injector' in name_lower or 'filter' in name_lower:
            categorized_parts['Engine'].append(p)
        elif 'battery' in name_lower or 'led' in name_lower or 'wire' in name_lower or 'bolt' in name_lower:
            categorized_parts['Electrical'].append(p)
        else:
            categorized_parts['General'].append(p)

    context = {
        'vehicles': Vehicle.objects.all().order_by('model_name'),
        'vehicle_types': VehicleType.objects.all(),
        'categorized_parts': categorized_parts,
        'active_issues_count': VehicleIssue.objects.filter(is_resolved=False).count(),
    }
    return render(request, 'fleet/admin_logistic_dashboard.html', context)

@login_required
def repairman_dashboard(request):
    """
    Mechanic Console: Processes ticket completion pipelines and defect tracking logs cleanly
    without variable scope bleed.
    """
    # Inside fleet/views.py -> def repairman_dashboard(request):
    if request.method == 'POST':
        if 'issue_id' in request.POST:
            issue_id = request.POST.get('issue_id')
            action_taken = request.POST.get('action_taken', 'Repaired')
            duration = request.POST.get('maintenance_duration', '')
        
            # 🌟 GET LIST OF ALL SELECTED PARTS
            part_ids = request.POST.getlist('consumed_part_ids') 
        
            issue = get_object_or_404(VehicleIssue, id=issue_id)
        
            if duration:
                issue.maintenance_duration = duration
                log_suffix = f" [Action: {action_taken} | Lifespan: {duration}]"
            else:
                issue.maintenance_duration = "Permanent Fix"
                log_suffix = f" [Action: {action_taken}]"

            issue.description += log_suffix

        # 🌟 LOOP THROUGH AND DEDUCT EACH SELECTED COMPONENT
            consumed_parts_names = []
            for p_id in part_ids:
                if p_id: # Skip empty options
                    part = get_object_or_404(Part, id=p_id)
                    if part.quantity > 0:
                        part.quantity -= 1
                        part.save()
                        consumed_parts_names.append(f"1x {part.name}")
                    else:
                        consumed_parts_names.append(f"0x {part.name} (Shortage)")

            if consumed_parts_names:
                issue.description += f" | Used: {', '.join(consumed_parts_names)}"

            issue.is_resolved = True
            issue.save()
        
            vehicle = issue.vehicle
            if not VehicleIssue.objects.filter(vehicle=vehicle, is_resolved=False).exists():
                vehicle.status = 'AVAILABLE'
                vehicle.save()
            
        return redirect('repairman_dashboard')
            
        # ---------------------------------------------------------------------
        # OPERATION B: LOG NEW DEFECT FAULT FLAG (Fixes the UnboundLocalError)
        # ---------------------------------------------------------------------
    elif 'vehicle' in request.POST and 'description' in request.POST:
            vehicle_id = request.POST.get('vehicle')
            description = request.POST.get('description')
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            
            # Saved with reported_by to clear the older integrity error constraint too
            VehicleIssue.objects.create(
                vehicle=vehicle, 
                description=description, 
                reported_by=request.user, 
                is_resolved=False
            )
            
            # Switch asset status to maintenance hold
            vehicle.status = 'MAINTENANCE'
            vehicle.save()
            return redirect('repairman_dashboard')

    # GET request processing context maps
    context = {
        'vehicles': Vehicle.objects.all().order_by('model_name'),
        'active_issues': VehicleIssue.objects.filter(is_resolved=False).order_by('-id'),
        'parts': Part.objects.all().order_by('name'),
    }
    return render(request, 'fleet/repairman_dashboard.html', context)