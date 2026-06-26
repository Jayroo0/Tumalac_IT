from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.views.decorators.http import require_http_methods
import traceback
from django.db.models import Q

from .models import VehicleType, Vehicle, Part, VehicleIssue, DashboardNotification
from .decorators import role_required


def manual_logout_view(request):
    """Bypasses standard 405 constraints by forcing a log out from a GET request."""
    django_logout(request)
    return redirect('login')


def custom_logout(request):
    """Fallback standard explicit dashboard logout trigger."""
    django_logout(request)
    return redirect('homepage')


def homepage(request):
    """
    Renders the public dashboard with guaranteed dynamic counters.
    """
    # Main grid tracking view only shows active, deployable assets
    vehicles = Vehicle.objects.filter(status='AVAILABLE').order_by('model_name')
    
    # Calculate global telemetry aggregates across systems
    total_fleet = Vehicle.objects.count()
    ready_deployment = Vehicle.objects.filter(status='AVAILABLE').count()
    in_maintenance = Vehicle.objects.filter(status='MAINTENANCE').count()
    active_flaws = VehicleIssue.objects.filter(is_resolved=False).count()
    
    context = {
        'vehicles': vehicles,
        'total_fleet': total_fleet,
        'ready_deployment': ready_deployment,
        'in_maintenance': in_maintenance,
        'active_flaw_count': active_flaws,
    }
    return render(request, 'fleet/homepage.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def dashboard_redirect(request):
    # 1. If the user is a superuser/system admin, send them straight to the Django Admin Backend
    if request.user.is_superuser:
        return redirect('/admin/')

    # 2. Force match our specific logistics profile user
    if request.user.username == 'pdrrmo_logistic':
        return redirect('admin_logistic_dashboard')
        
    # 3. Case-insensitive group check fallback for standard staff
    elif request.user.is_staff or request.user.groups.filter(name__iexact='staff').exists():
        return redirect('admin_logistic_dashboard')
        
    # 4. Repairman group check fallback
    elif request.user.groups.filter(name__iexact='repairman').exists():
        return redirect('repairman_dashboard')
        
    # 5. Safe fallback if all else fails
    return redirect('homepage')


@login_required
def admin_logistic_dashboard(request):
    """
    Logistics Panel: Tracks asset assignments and parts stock optimization controls.
    """



    print("!!! INSIDE LOGISTICS DASHBOARD VIEW FUNCTION !!!")
    
    # Securely restrict dashboard access via inline Python logic instead
    if not (request.user.is_staff or request.user.is_superuser or request.user.username == 'pdrrmo_logistic'):
        return redirect('homepage')
        
    print("!!! SUCCESS: pdrrmo_logistic successfully bypassed security checks !!!")
    




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

    # Read operations and inventory sorting matrix
    parts_list = Part.objects.all().order_by('name')
    categorized_parts = {
        'Engine': [],
        'Tires': [],
        'Electrical': [],
        'General': []
    }
    
    for p in parts_list:
        name_lower = p.name.lower()
        desc_lower = p.description.lower() if p.description else ""
        
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
@role_required(allowed_roles=['Repairman'])
def repairman_dashboard(request):
    """
    Mechanic Console: Processes ticket completion pipelines AND handles
    incoming new damage ticket dispatch creation logs cleanly.
    """
    if request.method == 'POST':
        # 🌟 ACTION 1: REPAIRMAN IS RESOLVING AN ISSUE ("FIX" BUTTON CLICKED)
        if 'issue_id' in request.POST:
            issue_id = request.POST.get('issue_id')
            action_taken = request.POST.get('action_taken', 'Repaired')
            duration = request.POST.get('maintenance_duration', '')
            part_ids = request.POST.getlist('consumed_part_ids') 
            remarks = request.POST.get('repairman_remarks', '').strip()
        
            issue = get_object_or_404(VehicleIssue, id=issue_id)
        
            log_suffix = f" [Action: {action_taken}"
            if duration:
                log_suffix += f" | Lifespan: {duration}]"
            else:
                log_suffix += "]"
            
            new_description = issue.description + log_suffix

            consumed_parts_names = []
            for p_id in part_ids:
                if p_id:
                    part = get_object_or_404(Part, id=p_id)
                    if part.quantity > 0:
                        part.quantity -= 1
                        part.save()
                        consumed_parts_names.append(f"1x {part.name}")

            if consumed_parts_names:
                new_description += f" | Used: {', '.join(consumed_parts_names)}"
            elif remarks:
                new_description += f" | Mechanic Remarks: {remarks}"

            VehicleIssue.objects.filter(id=issue_id).update(
                description=new_description,
                is_resolved=True
            )
            
            vehicle = issue.vehicle
            if not VehicleIssue.objects.filter(vehicle=vehicle, is_resolved=False).exclude(id=issue_id).exists():
                vehicle.status = 'AVAILABLE'
                vehicle.save()
                
            return redirect('repairman_dashboard')

        # 🌟 ACTION 2: REPAIRMAN IS REPORTING A NEW FAULT ("DISPATCH TICKET" CLICKED)
        elif 'vehicle' in request.POST and 'description' in request.POST:
            vehicle_id = request.POST.get('vehicle')
            description_text = request.POST.get('description', '').strip()
            
            if vehicle_id and description_text:
                target_vehicle = get_object_or_404(Vehicle, id=vehicle_id)
                
                # Create the new unresolved ticket entry in the database
                VehicleIssue.objects.create(
                    vehicle=target_vehicle,
                    reported_by=request.user,  # 🌟 FIX: Links the ticket to the current user session
                    description=description_text,
                    is_resolved=False
                )
                
                # Flag the vehicle status as MAINTENANCE so it is tracked correctly
                target_vehicle.status = 'MAINTENANCE'
                target_vehicle.save()
                
            return redirect('repairman_dashboard')

    # GET request processing: Query ONLY open, unresolved items.
    active_issues = VehicleIssue.objects.filter(is_resolved=False).order_by('-id')

    context = {
        'vehicles': Vehicle.objects.all().order_by('model_name'),
        'active_issues': active_issues,
        'parts': Part.objects.all().order_by('name'),
    }
    return render(request, 'fleet/repairman_dashboard.html', context)