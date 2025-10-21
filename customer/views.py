import random
from django.shortcuts import render, redirect,get_object_or_404
from django.views import View
from django.views.generic.edit import UpdateView
from django.urls import reverse_lazy
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from orders.models import Orders
from django.utils.encoding import force_bytes, force_str
from .models import OTP,Register, Customer ,UserAddress
from .forms import SignUpForm, LoginForm, OtpVerificationForm, ForgotPasswordForm,CustomSetPasswordForm,UserProfileForm,UpdateEmailForm,UserAddressForm
from django.contrib.auth.mixins import LoginRequiredMixin
from orders.models import OrderAddress
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from django.db import transaction
from .models import ReferralCode, Referral, ReferralReward
from offer.models import Offers
from datetime import timedelta
from .utils import create_referral_on_signup





User = get_user_model()

class MyLoginRequiredMixin(LoginRequiredMixin):    
    login_url = '/customer/'      
    redirect_field_name = 'home'  


def generate_and_send_otp(user):
    if isinstance(user, str):
        try:
            user = Register.objects.get(email=user)
            print(f"Converted email to user: {user}")
        except User.DoesNotExist:
            print("ERROR: No user found for this email.")
            return
    
    
    if not hasattr(user, 'email'):
        print("ERROR: Invalid user object")
        return
        
        
        
        
    otp_code = str(random.randint(100000, 999999))
    OTP.objects.update_or_create(     # pylint: disable=no-member
        user=user,
        defaults={'code': otp_code,
                  'created_at': timezone.now()})

    send_mail(
        'Your OTP for verification',
        f'Your one-time password is: {otp_code}',
        settings.EMAIL_HOST_USER,  
        [user.email],
        fail_silently=False
    )


@method_decorator(never_cache, name='dispatch') 
class ResendOtp(View):
    
    def get(self, request):
        email = request.session.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                generate_and_send_otp(user)
                # messages.success(request, "A new OTP has been sent to your email.",extra_tags='Resent-otp') 
                return redirect('otp-verification')
            except User.DoesNotExist:
                messages.error(request, "The user does not exist.",extra_tags='resent-otp')
                return redirect('signup')
        else:
            messages.error(request, "Session timed out. Please sign up again.")
            return redirect('signup')

@method_decorator(never_cache, name='dispatch') 
class SignUp(View):
    def get(self, request): 
        form = SignUpForm()
        referral_code = request.GET.get('ref', '')
        if referral_code:
            form.initial['referral_code'] = referral_code
        return render(request, 'customer/signup.html', {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            # try:
                with transaction.atomic():
                    # Create user
                    register_user = form.save(commit=False)
                    register_user.is_active = False
                    
                    # Get referral code from form
                    referral_code_input = form.cleaned_data.get('referral_code', '').strip().upper()
                    if referral_code_input:
                        register_user.referred_by_code = referral_code_input
                    
                    register_user.save()
                    # new_user = Register.objects.create_user(
                    # full_name=register_user.full_name,
                    # email=register_user.email,
                    # password=register_user.password
                    # )
                    
                    
                    # ref_code = request.GET.get('ref') or request.POST.get('referral_code') or request.session.get('referral_code')
        
                    # if ref_code:
                    #     result = create_referral_on_signup(new_user, ref_code)
                    #     if result['success']:
                    #         messages.success(
                    #             request, 
                    #             f" Welcome! You'll receive ₹50 bonus after your first purchase!"
                    #         )
                    #     else:
                    #         messages.warning(request, f"Referral code issue: {result['message']}")
                            
                    Customer.objects.create(user=register_user)
                    
                    new_code = ReferralCode.generate_unique_code(register_user)
                    ReferralCode.objects.create(user=register_user, code=new_code)
                    
                    if referral_code_input:
                        process_referral_signup(register_user, referral_code_input)
                    
                    generate_and_send_otp(register_user)
                    request.session["email"] = register_user.email
                    
                    messages.info(
                        request, 
                        "A verification code has been sent to your email. Please check your inbox."
                    )
                    return redirect('otp-verification')
                    
            # except Exception as e:
            #         messages.error(request, f"Error creating account: {str(e)}")
            #         return render(request, 'customer/signup.html', {'form': form})
        else:
            messages.error(request, "Please correct the errors in the form.",extra_tags='sign-up')
            return render(request, 'customer/signup.html', {'form': form})


def process_referral_signup(new_user, referral_code):
    try:
        referral_code_obj = ReferralCode.objects.get(code=referral_code)
        referrer = referral_code_obj.user
        
        if referrer == new_user:
            return
        
        referral = Referral.objects.create(
            referrer=referrer,
            referred=new_user,
            referral_code=referral_code_obj
        )
        
        referral_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        
        for offer in referral_offers:
            if offer.applies_to in ['referee', 'both']:
                ReferralReward.objects.create(
                    referral=referral,
                    user=new_user,
                    reward_type=ReferralReward.REFEREE_BONUS,
                    offer=offer,
                    discount_amount=offer.fixed_discount_amount or 0,
                    valid_from=timezone.now(),
                    valid_until=timezone.now() + timedelta(days=offer.validity_days)
                )
        
        messages.success(
            None,
            f' Referral code applied! You have special rewards waiting for you!'
        )
        
    except ReferralCode.DoesNotExist:
        messages.warning(None, 'Invalid referral code')
    except Exception as e:
        print(f"Error processing referral: {e}")


def process_first_purchase(user, order):
    try:
        referral = Referral.objects.filter(
            referred=user,
            first_purchase_at__isnull=True
        ).first()
        
        if not referral:
            return
        
        referral.first_purchase_at = timezone.now()
        referral.save()
        
        # Get active referral offers
        referral_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        
        for offer in referral_offers:
            # Create reward for referrer (person who referred)
            if offer.applies_to in ['referrer', 'both']:
                ReferralReward.objects.create(
                    referral=referral,
                    user=referral.referrer,
                    reward_type=ReferralReward.REFERRER_BONUS,
                    offer=offer,
                    discount_amount=offer.fixed_discount_amount or 0,
                    valid_from=timezone.now(),
                    valid_until=timezone.now() + timedelta(days=offer.validity_days)
                )
        
        # Update referral status
        referral.status = Referral.BOTH_REWARDED
        referral.save()
        
        messages.success(
            None,
            f' Your referrer has been rewarded for your purchase!'
        )
        
    except Exception as e:
        print(f"Error processing first purchase reward: {e}")

@method_decorator(never_cache, name='dispatch')
class LogIn(View):
    def get(self, request):
        form = LoginForm()
        return render(request, 'customer/login.html', {"form": form})

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if user.is_superuser:
                    messages.error(request, "Admin accounts cannot login here.",extra_tags='login-user')
                    return render(request, 'customer/login.html', {"form": form})
                
                login(request, user)
                messages.success(request, f"Welcome back, {user.email}!")
                return redirect('home')
            else:
                messages.error(request, "The user is not exist.\n Please create an account",extra_tags='login-user')
        
        return render(request, 'customer/login.html', {"form": form})

@never_cache
def Log_out(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        logout(request)
    return redirect('login')


@method_decorator(never_cache, name='dispatch') 
class OtpVerification(View):
    def get(self, request):
        form = OtpVerificationForm()
        return render(request, 'customer/otp_verification.html', {'form': form})
    
    def post(self, request):
        form = OtpVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']
            email = request.session.get('email')

            if not email:
                messages.error(request, "Session expired. Please sign up again.",extra_tags='otp-verification')
                return redirect('signup')

            try:
                user = Register.objects.get(email=email)
                otp_instance = OTP.objects.get(user=user) #pylint: disable=no-member

                if otp_instance.code == entered_otp and otp_instance.is_valid():
                    user.is_active = True
                    user.save()
                    
                    
                    if user.is_superuser:
                        messages.error(request, 'Admin accounts must use admin login.',extra_tags='otp-verification')
                        return redirect('admin_login')
                    
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    otp_instance.delete()
                    messages.success(request, 'Account verified successfully!')
                    return redirect('home')
                else:
                    messages.error(request, 'Invalid or expired OTP.',extra_tags='otp-verification')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please try signing up again.',extra_tags='otp-verification')
                return redirect('signup') 

            except OTP.DoesNotExist:                #pylint: disable=no-member
                messages.error(request, 'No OTP found for this user. Please request a new one.',extra_tags='otp-verification')

        return render(request, 'customer/otp_verification.html', {'form': form})

@method_decorator(never_cache, name='dispatch') 
class ForgotPassword(View):
    def get(self, request):
        print("got get request in the FORGOT PASSWORD function")

        form = ForgotPasswordForm()

        return render(request, 'customer/forgot_password.html', {'form': form})

    def post(self, request):
        print(" got POSST request in FORGOT PASSWORD")

        form = ForgotPasswordForm(request.POST)
        print(form)

        if form.is_valid():
            print('form is valid')
            
            email = form.cleaned_data['email']
            print(f"the entered email is {email}")
            
            

            try:
                user = User.objects.get(email=email) 
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                
                reset_link = request.build_absolute_uri(
                    reverse('change-password', kwargs={'uidb64': uidb64, 'token': token}))
                send_mail('Password reset request', f'Click here to set new password {reset_link}',
                          'fahimmuneer313@gmail.com', [user.email], fail_silently=False)

                messages.success(
                    request, "A link was sent to your mail to Reset your password.",extra_tags='otp-success')
                return redirect('login')
            except User.DoesNotExist as e :
                messages.error(
                    request, "The email you enetered does not registered.",extra_tags='forgot-password')
                print(f"the redirect error is {str(e)}")
                return redirect('forgot_password')
        messages.error(request, "Please enter a valid email.")
        print("please enter a valid email")
        return render(request,'customer/forgot_password.html',{'form':form})


@method_decorator(never_cache, name='dispatch') 
class ChangePassword(View):
    def get(self, request, uidb64, token):

        # decode the uidb64
        try : 
            u_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=u_id)
        except(ValueError,TypeError,User.DoesNotExist):
            user = None
        if user is not None and default_token_generator.check_token(user, token):

            form = CustomSetPasswordForm(user)

            return render(request, 'customer/change_password.html', {"form": form})
        messages.error(request,'The link was exhausted.',extra_tags='change-password')

    def post(self, request, uidb64, token):
        # decode the uidb64
        try:
            u_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=u_id)
        except (OverflowError, TypeError, ValueError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            form = CustomSetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password was changed successfully.")
                return redirect('login')
            else:
                return render(request, 'customer/change_password.html', {'form': form})
        
        messages.error(request, "The link is invalid or has expired. Please try again.",extra_tags='change-password')
        return redirect('forgot_password')


@method_decorator(never_cache, name='dispatch') 
class UserProfile(MyLoginRequiredMixin,View):
    
    login_url = 'login'   
    redirect_field_name = 'next'
    
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect('login')

        try:
            
            profile = Customer.objects.get(user=request.user) #pylint: disable=no-member
            # if profile is None:
            #     profile=Register.objects.create(
            #         full_name=request.user.first_name,
            #         email=request.user.email
                    
            #     )
        except Customer.DoesNotExist:  #pylint: disable=no-member
              profile=Customer.objects.create(user=request.user) #pylint: disable=no-member
              messages.warning(request, "Add a profile picture.",extra_tags='customer-profile')

        form = UserProfileForm(instance=profile)
        return render(request, 'customer/customer_profile.html', {
            'profile': profile,
            'form': form,
        })


@method_decorator(never_cache, name='dispatch') 
class EditPicture(MyLoginRequiredMixin,View):
    
    def get(self ,request ):
        profile = Customer.objects.get(user=request.user) #pylint: disable=no-member
        form = UserProfileForm(instance=profile)
        return render (request ,'customer/update_picture.html',{'form':form})
    
    
    def post(self, request):
        profile = Customer.objects.get(user=request.user)    #pylint: disable=no-member
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request,'Your profile picture was added.')
            return redirect('user_profile')
        messages.error(request,'Your uploading was failed. Please try again.',extra_tags='update-picture')
        print("redirecting to here and should show the message")
        return render(request ,'customer/update_picture.html',{'form':form})

@method_decorator(never_cache, name='dispatch') 
class UpdateEmailAndFullName(MyLoginRequiredMixin, View):
    login_url = 'login'
    redirect_field_name = 'next'

    def get(self, request):
        user = request.user
        form = UpdateEmailForm(instance=user)
        return render(request, 'customer/update_email.html', {'form': form, 'user': user})

    def post(self, request):
        user = request.user
        form = UpdateEmailForm(request.POST, instance=user)
       
        if form.is_valid():
            old_email = user.email
            updated_user = form.save(commit=False)
            updated_user.is_active = False
            updated_user.save()
            generate_and_send_otp(updated_user)
            request.session["email"] = old_email
            messages.info(request, "Your email has been changed. A verification code has been sent to your new email. Please verify to continue.",extra_tags='update-email')
            return redirect('email_otp')                   
        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'customer/update_email.html', {'form': form, 'user': user})
                

@method_decorator(never_cache, name='dispatch')             
class ChangeEmailOtpVerification(View):
    def get(self, request):
        form = OtpVerificationForm()
        return render(request, 'customer/otp_verification.html', {'form': form})
    
    def post(self, request):
        form = OtpVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data['otp_code']
            email = request.session.get('email')

            if not email:
                messages.error(request, "Session expired. Please sign up again.")
                return redirect('user_profile')

            try:
                user = Register.objects.get(email=email)
                otp_instance = OTP.objects.get(user=user) #pylint: disable=no-member

                if otp_instance.code == entered_otp and otp_instance.is_valid():
                    user.is_active = True
                    user.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                    
                    otp_instance.delete()

                    messages.success(request, 'Account Updated successfully!')
                    return redirect('user_profile')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please try again.')
                return redirect('user_profile') 

            except OTP.DoesNotExist:                #pylint: disable=no-member
                messages.error(request, 'No OTP found for this user. Please request a new one.')

        return render(request, 'customer/otp_verification.html', {'form': form})  

@method_decorator(never_cache, name='dispatch') 
class CustomerAddress(MyLoginRequiredMixin,View):
    def get(self,request):
       

        user=request.user
        form = UserAddress.objects.filter(user=user)   #pylint: disable=no-member
        profile = Customer.objects.get(user=request.user) #pylint: disable=no-member
        page=1
        if request.GET:
                page=request.GET.get('page',1)
        form_paginator=Paginator(form,1)
        form=form_paginator.get_page(page)
        
        
        return render (request,'customer/customer_address.html',{'form':form,'profile':profile})


@method_decorator(never_cache, name='dispatch') 
class AddCustomerAddress(MyLoginRequiredMixin,View):
    def get(self,request):
        form =UserAddressForm()
        return render(request,'customer/add_address.html',{'form':form})
    def post(self, request):
        form=UserAddressForm(request.POST)         
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if form.cleaned_data.get("is_default"):
                UserAddress.objects.filter(user=request.user, is_default=True).update(is_default=False) #pylint: disable=no-member
                address.is_default = True
            address.save()
        
        
            if address.is_default:                   #pylint: disable=no-member
                    OrderAddress.objects.create(    #pylint: disable=no-member
                    user=request.user,
                    mobile=form.cleaned_data['mobile'],
                    second_mob=form.cleaned_data.get('second_mob', ''),
                    address=form.cleaned_data['address'],
                    city=form.cleaned_data['city'],
                    state=form.cleaned_data['state'],
                    pin=form.cleaned_data['pin'],
                   
                
                    )
            
            
            messages.success(request,'Your address was added.')
            return redirect('user_address')
        
        messages.error(request,'Check your credentials.',extra_tags='add-customer-address')
        return render(request,'customer/add_address.html',{'form':form})

class EditAddress(MyLoginRequiredMixin,UpdateView):
    model = UserAddress
    fields =['mobile', 'second_mob', 'address', 'city', 'state', 'pin', 'address_type', 'is_default']
    template_name="customer/edit_address.html" 
    success_url=reverse_lazy("user_address" )  


class Orderlist(View):
    def get(self,request):
        pass