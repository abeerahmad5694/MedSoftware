from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from apps.users.models import Role, Permission
from django.contrib.auth.decorators import login_required

@login_required
def permissions(request):
    can_view, message = get_user_perms(request, 'manage_users')
    if not can_view:
        return redirect('page_not_found')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_role':
            name = request.POST.get('role_name')
            if name:
                # Create without company filter - use first company if exists
                from apps.configuration.models import Company
                comp = Company.objects.first()
                role, created = Role.objects.get_or_create(name=name, defaults={'company': comp})
                if not created and comp and role.company != comp:
                    # keep existing company
                    pass
                messages.success(request, f'Role "{name}" created.')
                return redirect(f"{request.path}?role_id={role.id}")
                
        elif action == 'delete_role':
            role_id = request.POST.get('role_id')
            role = get_object_or_404(Role, id=role_id)
            role.delete()
            messages.success(request, 'Role deleted.')
            return redirect('permissions')
            
        elif action == 'update_permissions':
            role_id = request.POST.get('role_id')
            role = get_object_or_404(Role, id=role_id)
            perms_codes = request.POST.getlist('permissions')
            print(f"=== SAVE DEBUG ===")
            print(f"Role ID: {role_id} Name: {role.name} Company: {role.company}")
            print(f"Codes from form: {perms_codes}")
            perms = Permission.objects.filter(code__in=perms_codes)
            print(f"Found perms in DB: {perms.count()} - {list(perms.values_list('code', flat=True))}")
            role.permissions.set(perms)
            print(f"After set: {role.permissions.count()}")
            print(f"==================")
            messages.success(request, f'Permissions updated: {perms.count()} saved.')
            return redirect(f"{request.path}?role_id={role.id}")

    # GET - NO company filter
    roles = Role.objects.all().order_by('id')
    active_role_id = request.GET.get('role_id')
    
    if active_role_id:
        try:
            active_role = Role.objects.get(id=active_role_id)
        except Role.DoesNotExist:
            active_role = roles.first()
    else:
        active_role = roles.first()

    all_perms = Permission.objects.all().order_by('module', 'name')
    modules = {}
    for p in all_perms:
        modules.setdefault(p.module, []).append(p)

    active_perms = []
    if active_role:
        active_perms = list(active_role.permissions.values_list('code', flat=True))
        print(f"DEBUG LOAD: Role={active_role.name} perms={active_perms}")

    return render(request, 'users/permissions.html', {
        'roles': roles,
        'active_role': active_role,
        'modules': modules,
        'active_perms': active_perms,
        'total_perms_count': all_perms.count(),
    })