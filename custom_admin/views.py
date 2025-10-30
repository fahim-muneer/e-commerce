# Update your custom_admin/views.py DashBoard class with this code

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic.edit import UpdateView, DeleteView
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib import messages
from .forms import AdminLoginForm,AdminProfileForm
from customer.models import Register,OTP
from django.db.models import Count, Sum, F
from django.db.models.functions import TruncMonth
from orders.models import Cart, Orders, OrderItem
from products.models import ProductPage
from category.models import CategoryPage
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.utils import timezone
from decimal import Decimal
import json
from django.core.mail import send_mail
import random
from customer.views import generate_and_send_otp


class AdminLoginMixin(LoginRequiredMixin):
    login_url = '/custom_admin/'
    redirect_field_name = 'next'


class LoginAdmin(View):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return redirect('dashboard')
            else:
                return redirect('home') 
        
        form = AdminLoginForm()
        return render(request, 'custom_admin/admin_login.html', {'form': form})

    def post(self, request):
        form = AdminLoginForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                if not user.is_superuser:
                    messages.error(request, "You don't have admin privileges.")
                    return render(request, 'custom_admin/admin_login.html', {'form': form})
                
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid credentials.")
        
        return render(request, 'custom_admin/admin_login.html', {'form': form})


@never_cache
def log_out(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            logout(request)
            return redirect('admin_login')
        else:
            return redirect('home')
    return redirect('admin_login')


@method_decorator(never_cache, name='dispatch')
class DashBoard(AdminLoginMixin, View):
    def get(self, request):
        # Get current date and year
        now = timezone.now()
        current_year = now.year
        
        # Basic Statistics
        total_user = Register.objects.filter(is_superuser=False).aggregate(total=Count("id"))['total'] or 0
        total_orders = Orders.objects.aggregate(total=Count("id"))['total'] or 0
        total_products = ProductPage.objects.aggregate(total=Count("id"))['total'] or 0
        total_category = CategoryPage.objects.aggregate(total=Count("id"))['total'] or 0
        
        # Total revenue from completed orders
        total_revenue = Orders.objects.filter(
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Get monthly sales data for current year
        monthly_sales = Orders.objects.filter(
            created_at__year=current_year,
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            total_sales=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('month')
        
        # Get monthly user registrations for current year
        monthly_users = Register.objects.filter(
            date_joined__year=current_year,
            is_superuser=False
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            user_count=Count('id')
        ).order_by('month')
        
        # Prepare data for charts (12 months)
        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                  'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        
        # Initialize arrays with zeros for all 12 months
        sales_data = [0] * 12
        users_data = [0] * 12
        
        # Fill in actual sales data
        for item in monthly_sales:
            if item['month']:
                month_index = item['month'].month - 1
                sales_data[month_index] = float(item['total_sales'] or 0)
        
        # Fill in actual user registration data
        for item in monthly_users:
            if item['month']:
                month_index = item['month'].month - 1
                users_data[month_index] = item['user_count']
        
        # Get top 10 selling products
        top_products = OrderItem.objects.filter(
            order__order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        ).values(
            'product__name',
            'product__id'
        ).annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:10]
        
        # Get top 10 selling categories
        top_categories = OrderItem.objects.filter(
            order__order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        ).values(
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            order_count=Count('order', distinct=True)
        ).order_by('-total_quantity')[:10]
        
        # Recent orders (last 10)
        recent_orders = Orders.objects.select_related('user').order_by('-created_at')[:10]
        
        context = {
            # Basic stats
            'total_user': total_user,
            'total_orders': total_orders,
            'total_products': total_products,
            'total_category': total_category,
            'total_revenue': total_revenue,
            'now': now,
            
            # Chart data (converted to JSON for JavaScript)
            'months': json.dumps(months),
            'sales_data': json.dumps(sales_data),
            'users_data': json.dumps(users_data),
            
            # Table data
            'top_products': top_products,
            'top_categories': top_categories,
            'recent_orders': recent_orders,
        }
        
        return render(request, 'custom_admin/dashboard.html', context)


def custom_404(request, exception):
    return render(request, '404.html', status=404)


def custom_500(request):
    return render(request, '500.html', status=500)


def custom_403(request, exception):
    return render(request, '403.html', status=403)


def custom_400(request, exception):
    return render(request, '400.html', status=400)


@method_decorator(never_cache, name='dispatch')
class AdminProfileView(AdminLoginMixin, View):
    def get(self, request):
        user = request.user
        form = AdminProfileForm(instance=user)
        print("Got GET request in AdminProfileView")
        return render(request, 'custom_admin/admin_profile.html', {'form': form})

    def post(self, request):
        print("Got POST request in AdminProfileView")
        user = request.user
        
        # Get form data
        new_email = request.POST.get('email', '').strip()
        new_full_name = request.POST.get('full_name', '').strip()
        profile_image = request.FILES.get('profile_image')
        
        print(f"Form data - Email: {new_email}, Name: {new_full_name}, Image: {profile_image}")
        
        try:
            # Validate required fields
            if not new_email or not new_full_name:
                messages.error(request, "Full name and email are required fields.",extra_tags='admin_profile')
                form = AdminProfileForm(instance=user)
                return render(request, 'custom_admin/admin_profile.html', {'form': form})
            
            # Validate email format
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(new_email)
            except ValidationError:
                messages.error(request, "Please enter a valid email address.",extra_tags='admin_profile')
                form = AdminProfileForm(instance=user)
                return render(request, 'custom_admin/admin_profile.html', {'form': form})
            
            # Check if email is being changed
            email_changed = (new_email != user.email)
            
            if email_changed:
                print(f"{user.full_name} is trying to change email from {user.email} to {new_email}")
                
                if Register.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "This email is already in use by another account.",extra_tags='admin_profile')
                    form = AdminProfileForm(instance=user)
                    return render(request, 'custom_admin/admin_profile.html', {'form': form})
                
                request.session['new_email'] = new_email
                request.session['old_email'] = user.email
                request.session['user_id'] = user.id
                
                request.session['pending_full_name'] = new_full_name
                if profile_image:
                    messages.info(request, "Please update your profile picture separately after email verification.")
                
                print(f"Sending OTP to old email: {user.email}")
                try:
                    generate_and_send_otp(user.email)
                    messages.info(request, f"We've sent a verification code to your current email ({user.email}). Please enter it to confirm the email change.",extra_tags='admin_profile')
                    print(f"OTP sent successfully to {user.email}")
                    return redirect('verify_email_otp')
                except Exception as e:
                    messages.error(request, f"Failed to send verification code: {str(e)}",extra_tags='admin_profile')
                    print(f"Error sending OTP: {str(e)}")
                    form = AdminProfileForm(instance=user)
                    return render(request, 'custom_admin/admin_profile.html', {'form': form})
            
            # If email is NOT being changed, update other fields directly
            else:
                print("Email not changed, updating other fields directly")
                
                # Update full name
                if new_full_name != user.full_name:
                    user.full_name = new_full_name
                    print(f"Full name updated to: {new_full_name}")
                
                if profile_image:
                    if not profile_image.content_type.startswith('image/'):
                        messages.error(request, "Please upload a valid image file.",extra_tags='admin_profile')
                        form = AdminProfileForm(instance=user)
                        return render(request, 'custom_admin/admin_profile.html', {'form': form})
                    
                    if profile_image.size > 5 * 1024 * 1024:
                        messages.error(request, "Image size must be less than 5MB.",extra_tags='admin_profile')
                        form = AdminProfileForm(instance=user)
                        return render(request, 'custom_admin/admin_profile.html', {'form': form})
                    
                    user.profile_image = profile_image
                    print(f"Profile image updated")
                
                user.save()
                messages.success(request, "Profile updated successfully!",extra_tags='admin_profile')
                print("Profile updated successfully (no email change)")
                return redirect('admin_profile')
            
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}",extra_tags='admin_profile')
            print(f"Exception in AdminProfileView: {str(e)}")
            import traceback
            traceback.print_exc()
        
        form = AdminProfileForm(instance=user)
        return render(request, 'custom_admin/admin_profile.html', {'form': form})


@method_decorator(never_cache, name='dispatch')
class VerifyEmailOtpView(AdminLoginMixin, View):
    def get(self, request):
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        
        if not (old_email and new_email):
            messages.error(request, "Session expired. Please try updating your profile again.",extra_tags='admin_profile')
            return redirect('admin_profile')
        
        print(f"GET request in VerifyEmailOtpView - Old: {old_email}, New: {new_email}")
        return render(request, 'custom_admin/verify_email.html', {
            'old_email': old_email,
            'new_email': new_email
        })

    def post(self, request):
        entered_otp = request.POST.get('otp_code', '').strip()
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        user_id = request.session.get('user_id')
        pending_full_name = request.session.get('pending_full_name')

        print(f"POST request - Entered OTP: {entered_otp}")
        print(f"Session data - Old: {old_email}, New: {new_email}, User ID: {user_id}")

        if not all([old_email, new_email, user_id]):
            messages.error(request, "Session expired. Please try again.",extra_tags='admin_profile')
            return redirect('admin_profile')

        if len(entered_otp) != 6:
            messages.error(request, "Please enter a valid 6-digit code.",extra_tags='admin_profile')
            return render(request, 'custom_admin/verify_email.html', {
                'old_email': old_email,
                'new_email': new_email
            })

        try:
            user = Register.objects.get(id=user_id, email=old_email)
            print(f"User found: {user.full_name}")
            
            otp_obj = OTP.objects.filter(user=user).order_by('-created_at').first()
            
            if not otp_obj:
                messages.error(request, "No OTP found. Please request a new one.",extra_tags='admin_profile')
                print("No OTP found in database")
                return render(request, 'custom_admin/verify_email.html', {
                    'old_email': old_email,
                    'new_email': new_email
                })
            
            print(f"OTP from DB: {otp_obj.code}, Entered: {entered_otp}")
            
            if otp_obj.code == entered_otp:
                print("OTP verified successfully")
                
                if Register.objects.filter(email=new_email).exclude(id=user.id).exists():
                    messages.error(request, "This email is now taken by another user. Please try a different email.",extra_tags='admin_profile')
                    self.clear_session_data(request)
                    return redirect('admin_profile')
                
                user.email = new_email
                user.username = new_email  
                
                if pending_full_name and pending_full_name != user.full_name:
                    user.full_name = pending_full_name
                    print(f"Full name also updated to: {pending_full_name}")
                
                user.save()
                print(f"Email updated from {old_email} to {new_email}")
                
                otp_obj.delete()
                print("OTP deleted")
                
                self.clear_session_data(request)
                
                messages.success(request, "Your email has been updated successfully!",extra_tags='admin_profile')
                return redirect('admin_profile')
            else:
                messages.error(request, "Invalid verification code. Please try again.",extra_tags='admin_profile')
                print("OTP mismatch")
                return render(request, 'custom_admin/verify_email.html', {
                    'old_email': old_email,
                    'new_email': new_email
                })

        except Register.DoesNotExist:
            messages.error(request, "User not found. Please log in again.",extra_tags='admin_profile')
            print("User not found")
            self.clear_session_data(request)
            return redirect('admin_login')
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}",extra_tags='admin_profile')
            print(f"Exception in VerifyEmailOtpView: {str(e)}")
            import traceback
            traceback.print_exc()
            return render(request, 'custom_admin/verify_email.html', {
                'old_email': old_email,
                'new_email': new_email
            })
    
    def clear_session_data(self, request):
        """Helper method to clear session data"""
        session_keys = ['new_email', 'old_email', 'user_id', 'pending_full_name']
        for key in session_keys:
            if key in request.session:
                del request.session[key]


@method_decorator(never_cache, name='dispatch')
class ResendOtp(AdminLoginMixin, View):
    def get(self, request):
        old_email = request.session.get('old_email')
        new_email = request.session.get('new_email')
        user_id = request.session.get('user_id')
        
        print(f"ResendOtp - Old: {old_email}, New: {new_email}, User ID: {user_id}")
        
        if not all([old_email, user_id]):
            messages.error(request, "Session expired. Please try updating your profile again.",extra_tags='re-otp')
            return redirect('admin_profile')
        
        try:
            user = Register.objects.get(id=user_id, email=old_email)
            
            OTP.objects.filter(user=user).delete()
            print(f"Old OTPs deleted for user {user.username}")
            
            generate_and_send_otp(old_email)
            messages.success(request, f"A new verification code has been sent to {old_email}.",extra_tags='re-otp')
            print(f"New OTP sent to {old_email}")
            
            return redirect('verify_email_otp')
            
        except Register.DoesNotExist:
            messages.error(request, "User not found. Please log in again.",extra_tags='re-otp')
            print("User not found in ResendOtp")
            return redirect('admin_login')
        except Exception as e:
            messages.error(request, f"Failed to resend code: {str(e)}",extra_tags='re-otp')
            print(f"Exception in ResendOtp: {str(e)}")
            return redirect('verify_email_otp')


@method_decorator(never_cache, name='dispatch')
class AdminChangePasswordView(AdminLoginMixin, View):
    
    def post(self, request):
        old_password = request.POST.get('old_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        user = request.user
        
        if not all([old_password, new_password, confirm_password]):
            messages.error(request, "All password fields are required.",extra_tags='admin_password')
            return redirect('admin_profile')
        
        if not user.check_password(old_password):
            messages.error(request, "Current password is incorrect.",extra_tags='admin_password')
            return redirect('admin_profile')
        
        if new_password != confirm_password:
            messages.error(request, "New password and confirmation password do not match.",extra_tags='admin_password')
            return redirect('admin_profile')
        
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.",extra_tags='admin_password')
            return redirect('admin_profile')
        
        if old_password == new_password:
            messages.error(request, "New password must be different from current password.",extra_tags='admin_password')
            return redirect('admin_profile')
        
        try:
            user.set_password(new_password)
            user.save()
            
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            messages.success(request, "Your password has been changed successfully!",extra_tags='admin_password')
            print(f"Password changed successfully for user: {user.username}")
            
        except Exception as e:
            messages.error(request, f"An error occurred while changing password: {str(e)}",extra_tags='admin_password')
            print(f"Error changing password: {str(e)}")
        
        return redirect('admin_profile')