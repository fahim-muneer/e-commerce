# customer/urls.py - COMPLETE FIXED VERSION

from django.urls import path
from .views import (
    LogIn,
    SignUp,
    Log_out,
    OtpVerification,
    ResendOtp,
    ForgotPassword,
    ChangePassword,
    UserProfile,
    EditPicture,
    UpdateEmailAndFullName,
    VerifyEmailOTP,           
    ResendEmailOTP,           
    CustomerAddress,
    AddCustomerAddress,
    EditAddress
)
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache


urlpatterns = [
    path('', never_cache(LogIn.as_view()), name="login"),
    path('signup/', never_cache(SignUp.as_view()), name='signup'),
    path('logout/', login_required(Log_out), name="logout"),
    path('otp/', OtpVerification.as_view(), name='otp-verification'),
    path('resend_otp/', ResendOtp.as_view(), name="resend_otp"),
    path('forgot_password/', ForgotPassword.as_view(), name='forgot_password'),
    path('change_password/<uidb64>/<token>', ChangePassword.as_view(), name="change-password"),
    path('user_profile/', login_required(UserProfile.as_view()), name="user_profile"),
    path('update/', login_required(EditPicture.as_view()), name="edit_profile_picture"),
    path('update_email/', login_required(UpdateEmailAndFullName.as_view()), name="email_update"),
    path('email_update_otp/', login_required(VerifyEmailOTP.as_view()), name="email_otp"),  
    path('resend_email_otp/', login_required(ResendEmailOTP.as_view()), name="resend_email_otp"),  
    path('user_address/', login_required(CustomerAddress.as_view()), name="user_address"),
    path('add_address/', login_required(AddCustomerAddress.as_view()), name="add_address"),
    path('<pk>/update/', login_required(EditAddress.as_view()), name="edit_address"),
]