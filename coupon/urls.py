from django.urls import path
from . import views
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('', staff_member_required(views.coupon_list), name='coupon_list'),
    path('remove/',views.remove_coupon, name='remove_coupon'),
    path('coupons/create/', staff_member_required(views.create_coupon), name='create_coupon'),
    path('coupons/update/<int:coupon_id>/', staff_member_required(views.update_coupon), name='update_coupon'),  
    path('coupons/delete/<int:coupon_id>/', staff_member_required(views.delete_coupon), name='delete_coupon'),
    path('applay_coupon/', views.apply_coupon, name="apply_coupon"),
    path('user_coupon_view/',views.user_coupon_list,name="user_coupon_list")
]
