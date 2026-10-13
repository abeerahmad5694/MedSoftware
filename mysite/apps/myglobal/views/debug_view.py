"""
Temporary debug view — add to URLs as path('debug/', debug_auth) then remove after diagnosis.
Access: https://abeer5694.pythonanywhere.com/debug/
"""
import os
from django.http import HttpResponse
from django.db import connection


def debug_auth(request):
    lines = []

    # 1. Environment
    lines.append("=== ENVIRONMENT ===")
    lines.append(f"PA_HOSTNAME env: {os.environ.get('PA_HOSTNAME', 'NOT SET')}")
    lines.append(f"LOCALAPPDATA env: {os.environ.get('LOCALAPPDATA', 'NOT SET')}")
    lines.append(f"os.name: {os.name}")

    # 2. Session
    lines.append("\n=== SESSION ===")
    lines.append(f"session key: {request.session.session_key}")
    lines.append(f"_auth_user_id in session: {request.session.get('_auth_user_id', 'NOT SET')}")

    # 3. Auth
    lines.append("\n=== AUTH ===")
    lines.append(f"request.user: {request.user}")
    lines.append(f"is_authenticated: {request.user.is_authenticated}")

    # 4. Cookies
    lines.append("\n=== COOKIES ===")
    for k, v in request.COOKIES.items():
        lines.append(f"  {k}: {str(v)[:50]}")

    # 5. Headers
    lines.append("\n=== KEY HEADERS ===")
    lines.append(f"HTTP_X_FORWARDED_PROTO: {request.META.get('HTTP_X_FORWARDED_PROTO', 'NOT SET')}")
    lines.append(f"HTTP_X_FORWARDED_FOR: {request.META.get('HTTP_X_FORWARDED_FOR', 'NOT SET')}")
    lines.append(f"SERVER_NAME: {request.META.get('SERVER_NAME', 'NOT SET')}")
    lines.append(f"request.is_secure(): {request.is_secure()}")
    lines.append(f"request.scheme: {request.scheme}")

    # 6. Django settings snapshot
    from django.conf import settings
    lines.append("\n=== SETTINGS ===")
    lines.append(f"SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
    lines.append(f"CSRF_COOKIE_SECURE: {settings.CSRF_COOKIE_SECURE}")
    lines.append(f"SESSION_COOKIE_SAMESITE: {getattr(settings, 'SESSION_COOKIE_SAMESITE', 'NOT SET')}")
    lines.append(f"SECURE_PROXY_SSL_HEADER: {getattr(settings, 'SECURE_PROXY_SSL_HEADER', 'NOT SET')}")
    lines.append(f"SESSION_ENGINE: {getattr(settings, 'SESSION_ENGINE', 'django.contrib.sessions.backends.db')}")

    # 7. DB check
    lines.append("\n=== DATABASE ===")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'django_session'")
            row = cursor.fetchone()
            lines.append(f"django_session table exists: {bool(row)}")
            if row:
                cursor.execute("SELECT COUNT(*) FROM django_session")
                count = cursor.fetchone()[0]
                lines.append(f"django_session rows: {count}")
    except Exception as e:
        lines.append(f"DB error: {e}")

    # 8. License path
    lines.append("\n=== LICENSE ===")
    try:
        from apps.users.views.licenseold import LICENSE_FILE
        lines.append(f"LICENSE_FILE: {LICENSE_FILE}")
        lines.append(f"file exists: {os.path.exists(LICENSE_FILE)}")
    except Exception as e:
        lines.append(f"License import error: {e}")

    return HttpResponse("<pre>" + "\n".join(lines) + "</pre>")
