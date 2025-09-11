from django.urls import path
from .views import LogIn,SignUp,Log_out,OtpVerification,ResendOtp,ForgotPassword,ChangePassword

urlpatterns = [
    path('',LogIn.as_view(),name="login"),
    path('signup/',SignUp.as_view(),name='signup'),
    path('logout/',Log_out , name="logut"),
    path('otp/',OtpVerification.as_view(),name='otp-verification'),
    path('resend_otp/',ResendOtp.as_view(),name="resend_otp"),
    path('forgot_password/',ForgotPassword.as_view(),name='forgot_password'),
    path('change_password/<uidb64>/<token>',ChangePassword.as_view(),name="change-password")
]
