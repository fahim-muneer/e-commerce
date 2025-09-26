from django.urls import path
from .views import VarientsView,AddVarients,UpdateVarients,DeleteVarients

urlpatterns = [
    path('varients/',VarientsView.as_view,name="varient_list"),
    path('add_varients/',AddVarients.as_view(),name="add_varient"),
    path('<int:pk>/update-varients/',UpdateVarients.as_view(),name="update_varient"),
    path('<int:pk>/delete-varients/',DeleteVarients.as_view(),name="delete_varient"),
    
    
]
