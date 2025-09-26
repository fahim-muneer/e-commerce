from django.urls import path
from .views import MyList,MyListDeleteItem

urlpatterns = [
    path('',MyList.as_view(),name="wish_list"),
    path('<int:pid>/delete/',MyListDeleteItem.as_view(),name="delete_item")
]
