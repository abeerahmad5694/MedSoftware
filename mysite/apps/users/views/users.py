from apps.myledger.services.helpers import get_user_perms
from django.shortcuts import redirect
from django.shortcuts import render

# def users(request):
#     return render(request, 'users/users.html')

from django.contrib.auth.models import User, Group
from django.contrib import messages
from apps.users.models import Role, Permission, UserProfile
from apps.configuration.models import Company, Branch, POSTerminal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404

@login_required

def users(request):
    can_view, message = get_user_perms(request, 'manage_users')
    if not can_view:
        return redirect('page_not_found')

    company = Company.objects.first()
    
    # -----------------------
    # CREATE / UPDATE USER
    # -----------------------
    if request.method == 'POST' and 'username' in request.POST:
        user_id = request.POST.get('user_id')
        username = request.POST.get('username')
        email = request.POST.get('email') if request.POST.get('email') not in('', None) else "abc@gmail.com"
        password = request.POST.get('password')
        role_id = request.POST.get('role')
        branch_id = request.POST.get('branch')
        terminal_id = request.POST.get('terminal')

        try:
            role = Role.objects.get(id=role_id, company=company)
        except (Role.DoesNotExist, ValueError):
            messages.error(request, 'Invalid role selected')
            return redirect('users')

        # UPDATE
        if user_id:
            user = get_object_or_404(User, pk=user_id)
            if user.username == 'VM':
                messages.error(request, 'VM CANNOT BE UPDATED')
                return redirect('users')
            user.username = username
            user.email = email if email else "abc@gmail.com"

            if password:
                user.set_password(password)

            user.save()
            
            # Handle Profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.company = company
            profile.branch_id = branch_id if branch_id else None
            profile.terminal_id = terminal_id if terminal_id else None
            profile.save()

            messages.success(request, 'User updated successfully')

        # CREATE
        else:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists')
                return redirect('users')

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Handle Profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.company = company
            profile.branch_id = branch_id if branch_id else None
            profile.terminal_id = terminal_id if terminal_id else None
            profile.save()

            messages.success(request, 'User created successfully')

        return redirect('users')

    # -----------------------
    # DELETE USER
    # -----------------------
    if request.method == 'POST' and request.POST.get('action') == 'delete':
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, pk=user_id)

        if user == request.user:
            messages.error(request, "You can't delete yourself")
        elif user.username == 'VM':
            messages.error(request, 'VM CANNOT BE DELETED')
        else:
            user.delete()
            messages.success(request, 'User deleted successfully')

        return redirect('users')

    # -----------------------
    # LIST USERS
    # -----------------------
    user_list = User.objects.all().order_by('username')
    roles = Role.objects.filter(company=company)
    branches = Branch.objects.all()
    terminals = POSTerminal.objects.all()

    # attach extra data for template
    for u in user_list:
        try:
            profile = u.userprofile if hasattr(u, 'userprofile') else None
            u.custom_role = profile.role.name if profile and profile.role else 'staff'
            u.role_code = profile.role.name.lower() if profile and profile.role else 'staff'
            u.branch_id = profile.branch.id if profile and profile.branch else ''
            u.terminal_id = profile.terminal.id if profile and profile.terminal else ''
        except Exception:
            u.custom_role = 'staff'
            u.role_code = 'staff'
            u.branch_id = ''
            u.terminal_id = ''

    return render(request, 'users/users.html', {
        'users': user_list,
        'roles': roles,
        'branches': branches,
        'terminals': terminals
    })


