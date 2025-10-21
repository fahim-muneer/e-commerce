from django.urls import path
from .views import VarientsView,AddVarients,UpdateVarients,DeleteVarients
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('varients/',staff_member_required(VarientsView.as_view()),name="varient_list"),
    path('add_varients/',staff_member_required(AddVarients.as_view()),name="add_varient"),
    path('<int:pk>/update-varients/',staff_member_required(UpdateVarients.as_view()),name="update_varient"),
    path('<int:pk>/delete-varients/',staff_member_required(DeleteVarients.as_view()),name="delete_varient"),
    
    
]
