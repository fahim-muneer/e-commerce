from django.urls import path
from .views import Category,CategoryAdd,DeleteCategory,UpdateCategory
from django.contrib.auth.decorators import login_required

urlpatterns = [
    
    path('category_list/',login_required(Category.as_view()),name="category_list"),
    path('category_add/',CategoryAdd.as_view(),name="add_category"),
    path('<pk>/category_update/',UpdateCategory.as_view(),name="update_category"),
    path('<pk>/category_delete/',DeleteCategory.as_view(),name="delete_category"),
    

]
