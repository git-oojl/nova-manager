# admin_core_RH/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login

def es_admin(user):
    return user.is_staff or user.is_superuser

def admin_required(redirect_to='no_permission'):
    """
    Decorator to require staff/superuser.
    - If not authenticated: redirect to login page.
    - If authenticated but not admin: redirect to 'redirect_to' view (default 'no_permission').
      You can set redirect_to='Menu' if you prefer immediate return to menu.
    It also adds a message so Menu page can show a toast if you prefer.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # not logged in -> standard redirect to login
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), login_url=None, redirect_field_name=REDIRECT_FIELD_NAME)

            # logged in but not admin -> redirect with message
            if not es_admin(request.user):
                # Add a message so the Menu page (or the no_permission page) can show a toast
                messages.warning(request, "Administrador requerido: No tienes permiso para acceder a esa página.")
                return redirect(redirect_to)

            # allowed
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator