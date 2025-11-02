from django.apps import AppConfig
from django.contrib import messages


class CustomerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer'

    def ready(self):
        """Import signals when app is ready"""
        
        import customer.signals
        
            
