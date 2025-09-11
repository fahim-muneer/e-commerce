import random
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from .models import OTP,Register
from .forms import SignUpForm, LoginForm, OtpVerificationForm, ForgotPasswordForm,CustomSetPasswordForm


User = get_user_model()



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



class ResendOtp(View):
    def get(self, request):
        email = request.session.get('email')
        if email:
            try:
                user = User.objects.get(email=email)
                generate_and_send_otp(user)
                messages.success(request, "A new OTP has been sent to your email.") 
                return redirect('otp-verification')
            except User.DoesNotExist:
                messages.error(request, "The user does not exist.")
                return redirect('signup')
        else:
            messages.error(request, "Session timed out. Please sign up again.")
            return redirect('signup')


class SignUp(View):
    def get(self, request):
        form = SignUpForm()
        return render(request, 'customer/signup.html', {'form': form})

    def post(self, request):
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  
            user.save()
            generate_and_send_otp(user)
            request.session["email"] = user.email
            messages.info(
                request, "A verification code has been sent to your email. Please check your inbox.")
            return redirect('otp-verification')
        else:
            messages.error(request, "Please correct the errors in the form.")
            return render(request, 'customer/signup.html', {'form': form})


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
                login(request, user)
                
                messages.success(request, f"Welcome back, {user.email}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
                
        
        return render(request, 'customer/login.html', {"form": form})


def Log_out(request):
    logout(request)
    return redirect('login')


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
                messages.error(request, "Session expired. Please sign up again.")
                return redirect('signup')

            try:
                # The user variable is now defined inside the try block
                user = Register.objects.get(email=email)
                otp_instance = OTP.objects.get(user=user) #pylint: disable=no-member

                if otp_instance.code == entered_otp and otp_instance.is_valid():
                    user.is_active = True
                    user.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                    
                    otp_instance.delete()

                    messages.success(request, 'Account verified successfully!')
                    return redirect('home')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except User.DoesNotExist:
                # Catch the User.DoesNotExist error here, before using the variable
                messages.error(request, 'User not found. Please try signing up again.')
                return redirect('signup') # Redirect to prevent further issues

            except OTP.DoesNotExist:                #pylint: disable=no-member
                # Catch the OTP.DoesNotExist error here
                messages.error(request, 'No OTP found for this user. Please request a new one.')

        return render(request, 'customer/otp_verification.html', {'form': form})

class ForgotPassword(View):
    def get(self, request):

        form = ForgotPasswordForm()

        return render(request, 'customer/forgot_password.html', {'form': form})

    def post(self, request):

        form = ForgotPasswordForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']

            try:
                user = User.objects.get(email=email) 
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

                
                reset_link = request.build_absolute_uri(
                    reverse('change-password', kwargs={'uidb64': uidb64, 'token': token}))
                send_mail('Password reset request', f'Click here to set new password {reset_link}',
                          'fahimmuneer313@gmail.com', [user.email], fail_silently=False)

                messages.success(
                    request, "A link was sent to your mail to Reset your password.")
                return redirect('login')
            except User.DoesNotExist:
                messages.error(
                    request, "The email you enetered does not registered.")
                return redirect('forgot_password')
        messages.error(request, "Please enter a valid email.")
        return render(request,'customer/forgot_password.html',{'form':form})


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
        messages.error(request,'The link was exhausted.')

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
        
        messages.error(request, "The link is invalid or has expired. Please try again.")
        return redirect('forgot_password')
