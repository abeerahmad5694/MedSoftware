"""Separate, CSRF-protected suggestion endpoint; never saves inventory."""
import json
import time

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.myglobal.services.helpers import get_user_perms
from apps.reports.services.urdu_names import suggest_names


@login_required
@require_POST
def urdu_name_suggestions(request):
    try:
        profile = request.user.userprofile
        if (not profile.role_id or not profile.company_id or not profile.branch_id
                or profile.branch.company_id != profile.company_id
                or not all(get_user_perms(request, p)[0] for p in ('view_inventory', 'edit_item'))):
            return JsonResponse({'error': 'Inventory view/edit permission and a valid company/branch are required.'}, status=403)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'A user profile is required.'}, status=403)
    try:
        payload = json.loads(request.body)
        names = payload.get('names') if isinstance(payload, dict) else None
        if (not isinstance(names, list) or not 1 <= len(names) <= 5
                or any(not isinstance(n, str) or not n.strip() or len(n) > 255 for n in names)):
            raise ValueError('Send 1–5 nonempty item names, each at most 255 characters.')
    except (ValueError, UnicodeDecodeError) as error:
        return JsonResponse({'error': str(error)}, status=400)
    # Use a shared Django cache in multi-worker deployments for a global limit.
    key = f'inventory-urdu-rate:{request.user.pk}:{int(time.time()) // 60}'
    cache.add(key, 0, 120)
    try:
        attempts = cache.incr(key)
    except ValueError:
        return JsonResponse({'error': 'Please retry shortly.'}, status=429)
    if attempts > 30:
        response = JsonResponse({'error': 'Suggestion limit reached. Please wait one minute.'}, status=429)
        response['Retry-After'] = '60'
        return response
    try:
        return JsonResponse({'results': suggest_names(names)})
    except ValueError as error:
        return JsonResponse({'error': str(error)}, status=400)