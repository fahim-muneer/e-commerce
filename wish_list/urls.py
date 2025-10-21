from django.urls import path
from .views import MyList,MyListDeleteItem
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('',login_required(MyList.as_view()),name="wish_list"),
    path('<int:pid>/delete/',login_required(MyListDeleteItem.as_view()),name="delete_item")
]
