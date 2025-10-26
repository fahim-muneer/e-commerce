from django.urls import path
from .views import LoginAdmin,DashBoard,log_out
from django.contrib.admin.views.decorators import staff_member_required



urlpatterns = [
path('',LoginAdmin.as_view(),name="admin_login"),

path('dashboard/',staff_member_required(DashBoard.as_view(),login_url='index'),name="dashboard"),
path('logout/',staff_member_required(log_out,login_url='index'), name='admin_logout')

]
