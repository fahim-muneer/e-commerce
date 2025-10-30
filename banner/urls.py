from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required
from .views import(
    AddBanner,DeleteBanner,EditBanner,BannerView
)

urlpatterns = [
    path('banner_view/',staff_member_required(BannerView.as_view(),login_url='/index/'),name="banner_view"),
    path('<pk>/banner_update/',staff_member_required(EditBanner.as_view(),login_url='/index/'),name="banner_update"),
    path('<pk>/banner_delete/',staff_member_required(DeleteBanner.as_view(),login_url='/index/'),name="banner_delete"),
    path('add_banner/',staff_member_required(AddBanner.as_view(),login_url='/index/'),name="add_banner"),
]
