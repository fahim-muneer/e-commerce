from django.apps import AppConfig


class CustomerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'customer'

    def ready(self):
        """Import signals when app is ready"""
        try:
            import customer.signals
            print("✅ Customer signals loaded successfully")
        except ImportError as e:
            print(f"⚠️ Could not import customer signals: {e}")
            
