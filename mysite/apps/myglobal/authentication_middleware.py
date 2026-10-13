from django.shortcuts import redirect, render
from django.urls import reverse
from datetime import datetime , timezone
from django.conf import settings
from django.utils.timezone import now
class loginrequiredmiddleware:
    def __init__(self,get_response):
        self.get_response = get_response
    
    
    def __call__(self,request):
        path = request.path_info
        if (
            path.startswith('/admin') or 
            path.startswith('/debug/') or   # TEMP: remove after diagnosis
            path.startswith(settings.STATIC_URL) or 
            path.startswith(settings.MEDIA_URL) or 
            path == '/favicon.ico' or 
            path == settings.LOGIN_URL or
            path == settings.LOGOUT_URL or
            path.startswith(settings.LOGIN_URL)  # covers /login/?next=...
        ):
            return self.get_response(request)
            
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.get_full_path()}")

        return self.get_response(request)



class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')

            if last_activity:
                last_activity_time = now().timestamp()
                if now().timestamp() - last_activity > 1600:
                    from django.contrib.auth import logout
                    logout(request)
                    return redirect(reverse('login'))

            request.session['last_activity'] = now().timestamp()

        return self.get_response(request)