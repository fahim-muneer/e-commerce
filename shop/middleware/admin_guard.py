from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class AdminAccessMiddleware:
    """Restrict access to /custom-admin/ URLs for non-staff users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith('/custom_admin/'):
            if not request.user.is_authenticated:
                messages.error(request, "Please log in as admin to access this page.")
                print("the request.user.is not authenticated ")
                return redirect('cusotm_admin/')

            if not request.user.is_staff:
                messages.error(request, "Access denied! Staff only area.")
                print("the page access is denied for non staff users sorry for that ")
                return redirect('home')  
        return self.get_response(request)
