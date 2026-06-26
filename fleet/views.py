from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as django_logout
from django.views.decorators.http import require_http_methods
import traceback
from django.db.models import Q
from django.contrib import messages
from .models import Vehicle, Part, Issue
from .models import VehicleType, Vehicle, Part, VehicleIssue, DashboardNotification
from .decorators import role_required


@login_required
@require_http_methods(["POST"])
def process_fix_issue(request, issue_id):
    """ Processes the consumption of parts and resolves active vehicle tasks """
    print(f"!!! PROCESSING TASK RESOLUTION FOR ISSUE ID: {issue_id} !!!")
    
    # 1. Grab parameters using your exact original fallback payload naming keys
    action_taken = request.POST.get('action_taken', 'Repaired')
    duration = request.POST.get('maintenance_duration', '')
    remarks = request.POST.get('repairman_remarks', '').strip()
    
    # Safely parse the comma-separated parts string mapped from our frontend script
    parts_raw = request.POST.get('consumed_part_ids', '')
    part_ids = [pid.strip() for pid in parts_raw.split(',') if pid.strip()]
    
    # 2. Look up the primary task object
    issue = get_object_or_404(VehicleIssue, id=issue_id)
    
    # 3. Restore your exact original log string format builder logic
    log_suffix = f" [Action: {action_taken}"
    if duration:
        log_suffix += f" | Lifespan: {duration}]"
    else:
        log_suffix += "]"
        
    new_description = issue.description + log_suffix

    # 4. Process and document component inventory deductions
    consumed_parts_names = []
    for p_id in part_ids:
        if p_id:
            part = get_object_or_404(Part, id=p_id)
            if part.quantity > 0:
                part.quantity -= 1
                part.save()
                consumed_parts_names.append(f"1x {part.name}")

    # Append component tracking lists or fallback manual comments to description
    if consumed_parts_names:
        new_description += f" | Used: {', '.join(consumed_parts_names)}"
    elif remarks:
        new_description += f" | Mechanic Remarks: {remarks}"

    # 5. Commit state updates back into database storage row
    VehicleIssue.objects.filter(id=issue_id).update(
        description=new_description,
        is_resolved=True
    )
    
    # 6. Release vehicle back to active operational duty if no open flaws remain
    vehicle = issue.vehicle
    if not VehicleIssue.objects.filter(vehicle=vehicle, is_resolved=False).exclude(id=issue_id).exists():
        vehicle.status = 'AVAILABLE'
        vehicle.save()
        
    messages.success(request, f"Maintenance action performed successfully for item {issue_id}!")
    return redirect('land_mobile_dashboard')


def manual_logout_view(request):
    django_logout(request)
    return redirect('login')


def custom_logout(request):
    django_logout(request)
    return redirect('homepage')


def homepage(request):
    """
    Renders the public dashboard with guaranteed dynamic counters.
    """
    # 1. Fetch all active, unresolved issues from the database
    active_issues_query = VehicleIssue.objects.filter(is_resolved=False)
    
    # 2. Extract unique vehicle IDs that have active issues
    # .values_list('vehicle_id', flat=True) extracts just the numbers [1, 4, 7]
    # .distinct() makes sure each vehicle ID is only listed once
    broken_vehicle_ids = active_issues_query.values_list('vehicle_id', flat=True).distinct()
    
    # 3. Compute our dynamic telemetry aggregates safely
    total_fleet = Vehicle.objects.count()
    
    # In maintenance is simply the total count of those unique broken vehicle IDs
    in_maintenance = len(broken_vehicle_ids)
    
    # Ready for deployment are vehicles that DO NOT have active issues
    ready_deployment = Vehicle.objects.exclude(id__in=broken_vehicle_ids).count()
    
    # Active flaws count is the raw total of open tickets
    active_flaws = active_issues_query.count()
    
    # 4. Filter the homepage main display grid to only show truly clean/available vehicles
    vehicles = Vehicle.objects.exclude(id__in=broken_vehicle_ids).order_by('model_name')
    
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
    if request.user.is_superuser:
        return redirect('/admin/')
    if request.user.username == 'pdrrmo_seacraft':
        return redirect('seacraft_dashboard')
    if request.user.username == 'pdrrmo_logistic':
        return redirect('admin_logistic_dashboard')
    if request.user.username in ['pdrrmo_repairman', 'repairman']:
        return redirect('land_mobile_dashboard')

    user_groups_lower = [g.name.lower() for g in request.user.groups.all()]
    if 'seacraft repairman' in user_groups_lower or 'seacraft technician' in user_groups_lower:
        return redirect('seacraft_dashboard')
    elif 'staff' in user_groups_lower or request.user.is_staff:
        return redirect('admin_logistic_dashboard')
    elif 'repairman' in user_groups_lower:
        return redirect('land_mobile_dashboard')

    return redirect('homepage')


@login_required
def admin_logistic_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser or request.user.username == 'pdrrmo_logistic'):
        return redirect('homepage')
        
    if request.method == 'POST':
        if 'vehicle_id' in request.POST:
            vehicle_id = request.POST.get('vehicle_id')
            driver_name = request.POST.get('driver', '').strip()
            vehicle = get_object_or_404(Vehicle, id=vehicle_id)
            vehicle.assigned_driver = driver_name
            vehicle.save()
            return redirect('admin_logistic_dashboard')
            
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

    parts_list = Part.objects.all().order_by('name')
    categorized_parts = {'Engine': [], 'Tires': [], 'Electrical': [], 'General': []}
    
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
    return land_mobile_dashboard(request)


@login_required
def land_mobile_dashboard(request):
    if request.user.username in ['pdrrmo_repairman', 'repairman']:
        pass
    elif not (request.user.is_staff or request.user.is_superuser or request.user.groups.filter(name__iexact='repairman').exists()):
        return redirect('homepage')

    vehicles = Vehicle.objects.exclude(
        Q(vehicle_type__name__icontains='Sea') |
        Q(vehicle_type__name__icontains='Maritime') |
        Q(vehicle_type__name__icontains='Boat')
    )

    if request.method == 'POST':
        # Handler for New Damage Tickets
        if 'vehicle' in request.POST and 'description' in request.POST:
            vehicle_id = request.POST.get('vehicle')
            description_text = request.POST.get('description', '').strip()
            
            if vehicle_id and description_text:
                target_vehicle = get_object_or_404(Vehicle, id=vehicle_id)
                VehicleIssue.objects.create(
                    vehicle=target_vehicle,
                    reported_by=request.user,
                    description=description_text,
                    is_resolved=False
                )
                target_vehicle.status = 'maintenance'
                target_vehicle.save()
                messages.success(request, "New maintenance ticket dispatched successfully into current layout workspace queue.")
                
            return redirect('land_mobile_dashboard')

    active_issues = VehicleIssue.objects.filter(is_resolved=False).order_by('-id')
    context = {
        'vehicles': vehicles,
        'active_issues': active_issues,
        'parts': Part.objects.all().order_by('name'),
        'workshop_title': 'Land Mobile Workshop',
    }
    return render(request, 'fleet/repairman_dashboard.html', context)


@login_required
def seacraft_dashboard(request):
    if request.user.username == 'pdrrmo_seacraft':
        pass
    elif not (request.user.groups.filter(name__iexact='seacraft repairman').exists() or request.user.is_staff or request.user.is_superuser):
        return redirect('homepage')

    vehicles = Vehicle.objects.filter(
        Q(vehicle_type__name__icontains='Sea') | Q(vehicle_type__name__icontains='Maritime') | Q(vehicle_type__name__icontains='Boat')
    )
    context = {
        'workshop_title': 'Maritime Division Panel',
        'active_issues': Issue.objects.filter(status='OPEN', vehicle__vehicle_type__name__iexact='MARINE'),
        'vehicles': Vehicle.objects.filter(vehicle_type__name__iexact='MARINE'), # Case-insensitive fix
        'parts': Part.objects.all(),
    }
    return render(request, 'fleet/seacraft_dashboard.html', context)