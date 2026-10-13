"""
WSGI config for mysite project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

# import os

# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# application = get_wsgi_application()




import os
import time

from django.core.wsgi import get_wsgi_application


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'mysite.settings'
)

django_application = get_wsgi_application()


def application(environ, start_response):

    t0 = time.perf_counter()

    print(
        f"\n[WSGI START] "
        f"{environ.get('REQUEST_METHOD')} "
        f"{environ.get('PATH_INFO')}"
    )

    response = django_application(environ, start_response)

    elapsed = (time.perf_counter() - t0) * 1000

    print(
        f"[WSGI TOTAL] "
        f"{environ.get('PATH_INFO')} "
        f"{elapsed:.2f} ms"
    )

    return response