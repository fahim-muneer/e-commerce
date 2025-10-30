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


from allauth.socialaccount.models import SocialAccount



def is_google_user(user):
    return SocialAccount.objects.filter(user=user, provider='google').exists()






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
        if request.user.is_authenticated:
            return redirect('home')
        
        form = SignUpForm()
        
        referral_code = request.GET.get('ref', '').strip().upper()
        
        if referral_code:
            try:
                referral_code_obj = ReferralCode.objects.get(code=referral_code)
                if referral_code_obj.is_active:
                    form.initial['referral_code'] = referral_code
                    messages.info(
                        request,
                        f'Referral code "{referral_code}" applied! Complete signup to get rewards! 🎁'
                    )
                else:
                    messages.warning(request, 'This referral code is no longer active.')
            except ReferralCode.DoesNotExist:
                messages.warning(request, 'Invalid referral code.')
        
        return render(request, 'customer/signup.html', {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    register_user = form.save(commit=False)
                    register_user.is_active = False
                    
                    referral_code_input = form.cleaned_data.get('referral_code', '').strip().upper()
                    
                    if referral_code_input:
                        register_user.referred_by_code = referral_code_input
                    
                    register_user.save()
                    
                    Customer.objects.create(user=register_user)
                    
                    new_code = ReferralCode.generate_unique_code(register_user)
                    ReferralCode.objects.create(user=register_user, code=new_code)
                    
                    referral_success = False
                    if referral_code_input:
                        referral_success = process_referral_signup(register_user, referral_code_input)
                    
                    generate_and_send_otp(register_user)
                    request.session["email"] = register_user.email
                    
                    if referral_success:
                        messages.success(
                            request,
                            'Account created! Check your email for verification code. '
                            'You\'ll receive special rewards after your first purchase! '
                        )
                    else:
                        messages.success(
                            request,
                            'Account created successfully! Check your email for verification code.'
                        )
                    
                    return redirect('otp-verification')
                    
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
                print(f"the error is : {str(e)}")
                return render(request, 'customer/signup.html', {'form': form})
        else:
            messages.error(request, "Please correct the errors in the form.", extra_tags='sign-up')
            return render(request, 'customer/signup.html', {'form': form})

def process_referral_signup(new_user, referral_code):

    print("="*80)
    print(f" Starting referral signup process for: {new_user.email}")
    print(f" Referral code: {referral_code}")
    
    try:
        referral_code_obj = ReferralCode.objects.get(code=referral_code)
        referrer = referral_code_obj.user
        
        print(f" Referral code found. Referrer: {referrer.email}")
        
        if referrer == new_user:
            print(" Self-referral not allowed")
            return False
        
        if Referral.objects.filter(referred=new_user).exists():
            print(" User was already referred")
            return False
        
        referral = Referral.objects.create(
            referrer=referrer,
            referred=new_user,
            referral_code=referral_code_obj,
            status=Referral.PENDING
        )
        
        print(f" Referral record created: ID {referral.id}")
        
        now = timezone.now()
        referral_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        print(f"Found {referral_offers.count()} active referral offers")
        
        if not referral_offers.exists():
            print("No active referral offers found - Referral created but no rewards")
            return True
        
        rewards_created = 0
        for offer in referral_offers:
            print(f"\n Processing offer: {offer.name}")
            print(f"   - Applies to: {offer.applies_to}")
            print(f"   - Fixed amount: ₹{offer.fixed_discount_amount}")
            print(f"   - Percentage: {offer.percentage_discount}%")
            

            if offer.applies_to in ['referee', 'both', 'Referee', 'Both']:
                validity_days = getattr(offer, 'validity_days', 30) or 30
                
                reward = ReferralReward.objects.create(
                    referral=referral,
                    user=new_user,
                    reward_type=ReferralReward.REFEREE_BONUS,
                    offer=offer,
                    discount_amount=offer.fixed_discount_amount or 0,
                    valid_from=timezone.now(),
                    valid_until=timezone.now() + timedelta(days=validity_days)
                )
                
                rewards_created += 1
                print(f"    Referee reward created: ID {reward.id}")
                print(f"      Amount: ₹{reward.discount_amount}")
                print(f"      Valid until: {reward.valid_until.strftime('%Y-%m-%d')}")
            else:
                print(f"    Skipping - offer applies to: {offer.applies_to}")
        
        print(f"\n Process complete: {rewards_created} rewards created for referee")
        print("="*80)
        return True
        
    except ReferralCode.DoesNotExist:
        print(" Invalid referral code")
        print("="*80)
        return False
    except Exception as e:
        print(f" Error processing referral: {e}")
        import traceback
        traceback.print_exc()
        print("="*80)
        return False


def process_first_purchase(user, order):

    print("="*80)
    print(f" Processing first purchase for: {user.email}")
    print(f" Order ID: {order.order_Id}")
    
    try:
        # Check if this user was referred and hasn't made first purchase yet
        referral = Referral.objects.filter(
            referred=user,
            first_purchase_at__isnull=True
        ).first()
        
        if not referral:
            print(f"ℹ No pending referral found for user {user.email}")
            print("="*80)
            return None, None
        
        print(f"✓ Found referral: ID {referral.id}")
        print(f"   Referrer: {referral.referrer.email}")
        print(f"   Referred: {referral.referred.email}")
        
        referral.first_purchase_at = timezone.now()
        referral.first_order = order
        referral.save()
        
        print(f" Referral updated with first purchase timestamp")
        

        print(f"Signal will process wallet credits automatically")
        print("="*80)
        
        return referral, None
        
    except Exception as e:
        print(f" Error processing first purchase: {e}")
        import traceback
        traceback.print_exc()
        print("="*80)
        return None, None   
    
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
                    messages.error(request, "Admin accounts cannot login from  here.",extra_tags='login-user')
                    return render(request, 'customer/login.html', {"form": form})
                if user.is_active:
                    login(request, user)
                    messages.success(request, f"Welcome back, {user.email}!")
                    return redirect('index')
                else:
                    messages.error(request,'The user is not active ',extra_tags="login-user")
                    return render(request, 'customer/login.html', {"form": form})
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
              
        google_user = SocialAccount.objects.filter(user=request.user, provider='google').exists() if request.user.is_authenticated else False
        
        form = UserProfileForm(instance=profile)
        return render(request, 'customer/customer_profile.html', {
            'profile': profile,
            'form': form,
            'google_user':google_user
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
        old_email = user.email 
        
        form = UpdateEmailForm(request.POST, instance=user)
       
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            new_full_name = form.cleaned_data.get('full_name')
            
            if new_email and new_email != old_email:
                print(f"Email change detected: {old_email} → {new_email}")
                
                from customer.models import Register
                if Register.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "This email is already in use by another account.",extra_tags='otp-verification')
                    return render(request, 'customer/update_email.html', {'form': form, 'user': user})
                
                request.session['old_email'] = old_email
                request.session['new_email'] = new_email
                request.session['user_id'] = user.id
                
                if new_full_name and new_full_name != user.full_name:
                    request.session['pending_full_name'] = new_full_name
                
                try:
                    generate_and_send_otp(old_email)  
                    messages.info(
                        request, 
                        f"We've sent a verification code to your current email ({old_email}). Please enter it to confirm the email change."
                        ,extra_tags='otp-verification'
                    )
                    print(f"OTP sent to old email: {old_email}")
                    return redirect('email_otp')
                except Exception as e:
                    messages.error(request, f"Failed to send verification code: {str(e)}")
                    print(f"Error sending OTP: {str(e)}")
                    return render(request, 'customer/update_email.html', {'form': form, 'user': user})
            
            else:
                print("No email change, updating full name only")
                if new_full_name and new_full_name != user.full_name:
                    user.full_name = new_full_name
                    user.save()
                    messages.success(request, "Your profile has been updated successfully!")
                else:
                    messages.info(request, "No changes were made.")
                return redirect('profile') 
        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'customer/update_email.html', {'form': form, 'user': user})            





@method_decorator(never_cache, name='dispatch')
class VerifyEmailOTP(MyLoginRequiredMixin, View):
    """Handle OTP verification for email change"""
    
    def get(self, request):
        # Check if session data exists
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        
        if not (old_email and new_email):
            messages.error(request, "Session expired. Please try updating your email again.")
            return redirect('user_profile')
        
        form = OtpVerificationForm()
        return render(request, 'customer/otp_verification.html', {
            'form': form,
            'old_email': old_email,
            'new_email': new_email
        })
    
    def post(self, request):
        form = OtpVerificationForm(request.POST)
        
        if not form.is_valid():
            messages.error(request, "Please enter a valid OTP.")
            return render(request, 'customer/otp_verification.html', {'form': form})
        
        entered_otp = form.cleaned_data['otp_code']
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        user_id = request.session.get('user_id')
        pending_full_name = request.session.get('pending_full_name')
        
        print(f"OTP Verification - Entered: {entered_otp}")
        print(f"Session - Old: {old_email}, New: {new_email}, User ID: {user_id}")
        
        # Validate session data
        if not all([old_email, new_email, user_id]):
            messages.error(request, "Session expired. Please try again.")
            return redirect('user_profile')
        
        # Validate OTP length
        if len(entered_otp) != 6:
            messages.error(request, "Please enter a valid 6-digit code.")
            return render(request, 'customer/otp_verification.html', {
                'form': form,
                'old_email': old_email,
                'new_email': new_email
            })
        
        try:
            # Get user by ID and verify old email matches
            user = Register.objects.get(id=user_id, email=old_email)
            print(f"User found: {user.email}")
            
            # Get the most recent OTP for this user
            otp_obj = OTP.objects.filter(user=user).order_by('-created_at').first()
            
            if not otp_obj:
                messages.error(request, "No OTP found. Please request a new one.")
                print("No OTP found in database")
                return render(request, 'customer/otp_verification.html', {
                    'form': form,
                    'old_email': old_email,
                    'new_email': new_email
                })
            
            print(f"OTP from DB: {otp_obj.code}, Entered: {entered_otp}")
            
            # Check if OTP is still valid (not expired)
            if not otp_obj.is_valid():
                messages.error(request, "OTP has expired. Please request a new one.")
                print("OTP expired")
                return render(request, 'customer/otp_verification.html', {
                    'form': form,
                    'old_email': old_email,
                    'new_email': new_email
                })
            
            # Verify OTP matches
            if otp_obj.code == entered_otp:
                print("OTP verified successfully!")
                
                # Double-check new email is still available
                if Register.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "This email is now taken by another user. Please try a different email.")
                    self.clear_session_data(request)
                    return redirect('user_profile')
                
                # Update email
                user.email = new_email
                user.username = new_email  # Update username if based on email
                
                # Update full name if it was pending
                if pending_full_name and pending_full_name != user.full_name:
                    user.full_name = pending_full_name
                    print(f"Full name updated to: {pending_full_name}")
                
                user.save()
                print(f"Email updated from {old_email} to {new_email}")
                
                # Delete used OTP
                otp_obj.delete()
                print("OTP deleted")
                
                # Clear session data
                self.clear_session_data(request)
                
                # Keep user logged in (update session)
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                
                messages.success(request, "Your email has been updated successfully!")
                return redirect('user_profile')
            else:
                messages.error(request, "Invalid verification code. Please try again.")
                print("OTP mismatch")
                return render(request, 'customer/otp_verification.html', {
                    'form': form,
                    'old_email': old_email,
                    'new_email': new_email
                })
        
        except Register.DoesNotExist:
            messages.error(request, "User not found. Please log in again.")
            print("User not found")
            self.clear_session_data(request)
            return redirect('login')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            print(f"Exception in VerifyEmailOTP: {str(e)}")
            import traceback
            traceback.print_exc()
            return render(request, 'customer/otp_verification.html', {
                'form': form,
                'old_email': old_email,
                'new_email': new_email
            })
    
    def clear_session_data(self, request):
        """Helper method to clear session data"""
        session_keys = ['old_email', 'new_email', 'user_id', 'pending_full_name']
        for key in session_keys:
            if key in request.session:
                del request.session[key]


@method_decorator(never_cache, name='dispatch')
class ResendEmailOTP(MyLoginRequiredMixin, View):
    """Resend OTP for email verification"""
    
    def get(self, request):
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        user_id = request.session.get('user_id')
        
        print(f"ResendEmailOTP - Old: {old_email}, New: {new_email}, User ID: {user_id}")
        
        if not all([old_email, user_id]):
            messages.error(request, "Session expired. Please try updating your email again.")
            return redirect('user_profile')
        
        try:
            user = Register.objects.get(id=user_id, email=old_email)
            
            # Delete old OTPs for this user
            OTP.objects.filter(user=user).delete()
            print(f"Old OTPs deleted for user {user.email}")
            
            # Generate and send new OTP to OLD email
            generate_and_send_otp(old_email)
            messages.success(request, f"A new verification code has been sent to {old_email}.")
            print(f"New OTP sent to old email: {old_email}")
            
            return redirect('email_otp')
            
        except Register.DoesNotExist:
            messages.error(request, "User not found. Please log in again.")
            print("User not found in ResendEmailOTP")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"Failed to resend code: {str(e)}")
            print(f"Exception in ResendEmailOTP: {str(e)}")
            return redirect('email_otp')






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