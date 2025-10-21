from django.urls import path
from .views import Category,CategoryAdd,DeleteCategory,UpdateCategory
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required


urlpatterns = [
    
    path('category_list/',staff_member_required(Category.as_view()),name="category_list"),
    path('category_add/',staff_member_required(CategoryAdd.as_view()),name="add_category"),
    path('<pk>/category_update/',staff_member_required(UpdateCategory.as_view()),name="update_category"),
    path('<pk>/category_delete/',staff_member_required(DeleteCategory.as_view()),name="delete_category"),
    

]
