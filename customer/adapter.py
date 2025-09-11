# customer/adapter.py

from allauth.account.adapter import DefaultAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    """
    This class acts as a bridge between allauth and the user model.
    """
    
    def populate_username(self, request, user):
        """
        Overrides the default method to prevent allauth from trying to
        populate a 'username' field on the user model, which doesn't exist.
        """
        # This is the key fix: we do nothing here
        pass

    def save_user(self, request, user, form, commit=True):
        """
        This method is called to save the user.
        We'll use it to set the full_name field.
        """
        # Call the default allauth save process first
        user = super().save_user(request, user, form, commit)
        
        # Then, set your custom field
        user.full_name = form.cleaned_data.get('full_name')
        
        # Save the user with the new full_name
        user.save()
        
        return user