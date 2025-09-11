from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from datetime import timedelta
from django.utils import timezone

class MyAccountManager(BaseUserManager):
    def create_user(self , full_name , email , password=None):
        
        if not email :
            raise ValueError("Email must be set")
        if not full_name:
            raise ValueError()
        
        user = self.model(
            
            email=self.normalize_email(email),
            full_name=full_name,
        
        )
        
        user.set_password(password)
        user.is_active = True  
        user.save(using=self._db)
        return user
    
    def create_superuser(self, full_name, email, password):
        
        user = self.create_user(
            full_name=full_name,
            email=email,
            password=password,
        )
      
        user.is_admin = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class Register(AbstractBaseUser):
    full_name    = models.CharField(max_length=200, unique=False, blank=False)
    email        = models.EmailField(max_length=300, unique=True, blank=False)    
    date_joined  = models.DateTimeField(auto_now_add=True)
    last_login   = models.DateTimeField(auto_now_add=True)
    is_admin     = models.BooleanField(default=False)
    is_staff     = models.BooleanField(default=False)
    is_active    = models.BooleanField(default=True) 
    is_superuser = models.BooleanField(default=False)
    
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    objects = MyAccountManager()
    
    def __str__(self):
        return str(self.email)
    
    def has_perm(self, perm, obj=None):
       
        return self.is_superuser
    
    def has_module_perms(self, app_label):
       
        return self.is_superuser
    

class AddressType(models.Model):
    name = models.CharField(max_length=100)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)



class UserAddress(models.Model):
    user       = models.ForeignKey ( Register , on_delete = models.CASCADE )
    mobile     = models.CharField  (max_length=20 , blank=False , unique=False)
    second_mob = models.CharField  (max_length=20 , blank=True ,  unique=False)
    address    = models.CharField  (max_length=500 , blank=False  )
    city       = models.CharField  (max_length=300 , blank=False)
    state      = models.CharField  (max_length=200 , blank=False)
    pin        = models.IntegerField()
    country    = models.CharField  (max_length=100 , blank=False)
    address_type = models.ForeignKey(AddressType , on_delete=models.CASCADE)
    is_default = models.BooleanField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)    



class OTP(models.Model):
    user = models.OneToOneField(Register , on_delete=models.CASCADE)
    code = models.CharField(max_length=6 , unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def is_valid(self):
        expiration_time=self.created_at + timedelta(minutes=5)
        return timezone.now() <= expiration_time
    def __str__(self):
        return str(self.user)