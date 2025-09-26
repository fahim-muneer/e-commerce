from django.urls import path
from .views import UserPanel,BloackUser,DeleteUser


urlpatterns = [
    path('user_panel/',UserPanel.as_view(),name="user_panel"),
    path('block_user/<uid>/',BloackUser.as_view(),name="block_user"),
    path('delete_user/',DeleteUser.as_view(),name="delete_user")
]
