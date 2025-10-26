from django.urls import path
from .views import UserPanel,BloackUser,DeleteUser
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('user_panel/',staff_member_required(UserPanel.as_view(),login_url='index'),name="user_panel"),
    path('block_user/<uid>/',staff_member_required(BloackUser.as_view(),login_url='index'),name="block_user"),
    path('delete_user/',staff_member_required(DeleteUser.as_view(),login_url='index'),name="delete_user")
]
