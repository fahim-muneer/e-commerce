from django.urls import path
from .views import LoginAdmin,DashBoard,log_out,AdminProfileView,VerifyEmailOtpView,ResendOtp,AdminChangePasswordView
from django.contrib.admin.views.decorators import staff_member_required



urlpatterns = [
path('',LoginAdmin.as_view(),name="admin_login"),

path('dashboard/',staff_member_required(DashBoard.as_view(),login_url='index'),name="dashboard"),
path('logout/',staff_member_required(log_out,login_url='index'), name='admin_logout'),
path('admin_profile/',staff_member_required(AdminProfileView.as_view()),name='admin_profile'),
path('verify_email_otp/',staff_member_required(VerifyEmailOtpView.as_view()),name='verify_email_otp'),
path('resend-otp/', ResendOtp.as_view(), name='resend_otp'),
path('change-password/', AdminChangePasswordView.as_view(), name='admin_change_password'),



]
