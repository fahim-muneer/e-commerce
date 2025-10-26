from django.shortcuts import redirect,render
from django.contrib import messages
from django.core.exceptions import PermissionDenied, SuspiciousOperation, BadRequest
from django.urls import reverse, NoReverseMatch
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            
            # Intercept HTTP error status codes and convert to redirects with messages
            if response.status_code == 404:
                messages.error(request, "Page Not Found! The page you're looking for doesn't exist.", extra_tags="error_handler")
                print("====== page not found and this message is from error_midleware =====")
                return render(request,'errors/404.html')
            
            if response.status_code == 403:
                messages.error(request, "Access Forbidden! You don't have permission to access this resource.", extra_tags="error_handler")
                return redirect(reverse('index'))
            
            if response.status_code == 400:
                messages.error(request, "Bad Request! The request could not be processed.", extra_tags="error_handler")
                return redirect(reverse('index'))
            
            if response.status_code == 500:
                messages.error(request, "Internal Server Error! Something went wrong. Please try again later.", extra_tags="error_handler")
                return redirect(reverse('index'))
            
            return response

        except Http404:
            messages.error(request, "Page Not Found! The page you're looking for doesn't exist.", extra_tags="error_handler")
            return redirect(reverse('index'))

        except PermissionDenied:
            messages.error(request, "Access Denied! You don't have permission to view this page.", extra_tags="error_handler")
            return redirect(reverse('index'))

        except BadRequest:
            messages.error(request, "Bad Request! The request could not be processed.", extra_tags="error_handler")
            return redirect(reverse('index'))

        except SuspiciousOperation as e:
            messages.error(request, "Invalid Request! The operation you tried is not allowed.", extra_tags="error_handler")
            logger.warning(f"SuspiciousOperation: {e}")
            return redirect(reverse('index'))

        except NoReverseMatch:
            messages.error(request, "Oops! Something went wrong while loading the page.", extra_tags="error_handler")
            return redirect(reverse('index'))

        except Exception as e:
            messages.error(request, "An unexpected error occurred. Please try again later.", extra_tags="error_handler")
            logger.error(f"Unexpected Error: {e}", exc_info=True)
            print('=' * 100)
            print("Unexpected Error")
            print(f"{e}")
            print('=' * 100)
            return redirect(reverse('index'))

    def process_exception(self, request, exception):
        """
        Additional exception handler for uncaught exceptions
        """
        if isinstance(exception, Http404):
            messages.error(request, "Page Not Found! The page you're looking for doesn't exist.", extra_tags="error_handler")
            print("The page in not exist man")
            return redirect(reverse('index'))
        
        if isinstance(exception, PermissionDenied):
            messages.error(request, "Access Denied! You don't have permission to access this resource.", extra_tags="error_handler")
            return redirect(reverse('index'))
        
        # Let other exceptions be handled by Django's default handler
        return None