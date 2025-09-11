from django.urls import path
from .views import home,ProdectDetails,Index
urlpatterns = [
    path('home/',home, name="home"),
    path('<pk>/details/',ProdectDetails.as_view(),name="items_details"),
    path('',Index.as_view(),name="index")
    
]
