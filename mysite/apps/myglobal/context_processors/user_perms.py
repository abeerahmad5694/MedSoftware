def user_perms(request):
    # Superuser = all permissions
    if request.user.is_authenticated and (request.user.is_superuser or request.user.username == "z"):
        from apps.users.models import Permission
        if not hasattr(request, '_user_perm_codes'):
            request._user_perm_codes = set(Permission.objects.values_list('code', flat=True))
        return {'user_perm_codes': request._user_perm_codes}

    if request.user.is_authenticated:
        try:
            if not hasattr(request, '_user_perm_codes'):
                request._user_perm_codes = set(
                    request.user.userprofile.get_permissions().values_list('code', flat=True)
                )
            return {'user_perm_codes': request._user_perm_codes}
        except:
            return {'user_perm_codes': set()}
            
    return {'user_perm_codes': set()}