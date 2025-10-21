from django.urls import path
from .views import ReferralDashboard,ReferralDashboardView,ReferralDashboardView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
urlpatterns = [
    path('refferal_dashboard/',login_required(ReferralDashboard.as_view()),name='refferal_dashboard'),
    path('refferal_admin_dashboard/',staff_member_required(ReferralDashboardView.as_view()),name='admin_refferal_dashboard')
]
