from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def roles_required(*roles):
    """Restrict a view to superuser/admin or one of the given role codes."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_admin or request.user.is_staff:
                return view_func(request, *args, **kwargs)
            if request.user.role and request.user.role.code in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied('You do not have permission to access this module.')
        return wrapper
    return decorator


def module_access(module_code):
    """Restrict a view to users whose role grants access to the given module."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.has_module_access(module_code):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied('You do not have permission to access this module.')
        return wrapper
    return decorator