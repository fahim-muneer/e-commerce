from django.urls import path
from .views import LoginAdmin,DashBoard,log_out
from django.contrib.auth.decorators import login_required



urlpatterns = [
path('login/',LoginAdmin.as_view(),name="admin_login"),
path('dashboard/',login_required(DashBoard.as_view()),name="dashboard"),
path('logout/',log_out, name="admin_logout")

]
