from django.shortcuts import redirect
from django.urls import resolve

from django.utils.deprecation import MiddlewareMixin

class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    
class DisableClientCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, private, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class UserTypeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.user.is_authenticated:
            current_url_name = resolve(request.path_info).url_name
                       
            if request.user.is_superuser:
                user_only_views = ['user_profile', 'user_address', 'checkout']
                if current_url_name in user_only_views:
                    return redirect('dashboard')
            
            else:
                admin_only_views = ['dashboard', 'admin_login']
                if current_url_name in admin_only_views:
                    return redirect('home')
        
        response = self.get_response(request)
        return response 