from django.urls import path
from .views import (
    OfferView,
    AddOffer,
    UpdateOffer,
    DeleteOffer
    
)
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('offer/view/',staff_member_required(OfferView.as_view(),login_url='index'),name="offer_view"),
    path('add/offer/',staff_member_required(AddOffer.as_view(),login_url='index'),name="add_offer"),
    path('<int:pk>/update/offer/',staff_member_required(UpdateOffer.as_view(),login_url='index'),name="update_offer"),
    path('<int:pk>/delete/offer/',staff_member_required(DeleteOffer.as_view(),login_url='index'),name="delete_offer")
    
    
]
