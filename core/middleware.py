from django.shortcuts import redirect
from django.urls import Resolver404, resolve


class RequirePasswordChangeMiddleware:
    """Restrict provisioned users to password change or logout until reset."""

    exempt_url_names = {'password-change', 'logout'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and user.must_change_password:
            try:
                url_name = resolve(request.path_info).url_name
            except Resolver404:
                url_name = None
            if url_name not in self.exempt_url_names:
                return redirect('password-change')
        return self.get_response(request)
