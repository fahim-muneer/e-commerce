from django.urls import path
from .views import ReferralDashboard,ReferralDashboardView,ReferralListView,ReferralRewardListView,UserReferralDetailView
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
urlpatterns = [
    path('refferal_dashboard/',login_required(ReferralDashboard.as_view()),name='refferal_dashboard'),
    path('refferal_admin_dashboard/',staff_member_required(ReferralDashboardView.as_view(),login_url='index'),name='admin_refferal_dashboard'),
    path('user_refferal_detail/<int:user_id>',staff_member_required(UserReferralDetailView.as_view(),login_url='index'),name='admin_user_referral_detail'),
    path('admin/list/',staff_member_required(ReferralListView.as_view(), login_url='index'),name='admin_referral_list'),
    path('referrals/rewards/',staff_member_required(ReferralRewardListView.as_view(),login_url='index'),name='admin_reward_list'),
       
    ]
