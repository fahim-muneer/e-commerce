from django.urls import path
from .views import LogIn,SignUp,Log_out,OtpVerification,ResendOtp,ForgotPassword,ChangePassword,UserProfile,EditPicture,UpdateEmailAndFullName,ChangeEmailOtpVerification,CustomerAddress,AddCustomerAddress,EditAddress


urlpatterns = [
    path('',LogIn.as_view(),name="login"),
    path('signup/',SignUp.as_view(),name='signup'),
    path('logout/',Log_out , name="logout"),
    path('otp/',OtpVerification.as_view(),name='otp-verification'),
    path('resend_otp/',ResendOtp.as_view(),name="resend_otp"),
    path('forgot_password/',ForgotPassword.as_view(),name='forgot_password'),
    path('change_password/<uidb64>/<token>',ChangePassword.as_view(),name="change-password"),
    path('user_profile/',UserProfile.as_view(),name="user_profile"),
    path('update/',EditPicture.as_view(),name="edit_profile_picture"),
    path('update_email/',UpdateEmailAndFullName.as_view(),name="email_update"),
    path('email_update_otp/',ChangeEmailOtpVerification.as_view(),name="email_otp"),
    path('user_address/',CustomerAddress.as_view(),name="user_address"),
    path('add_address/',AddCustomerAddress.as_view(),name="add_address"),
    path('<pk>/update/',EditAddress.as_view(),name="edit_address"),

]
