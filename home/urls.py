from django.urls import path
from .views import home,ProdectDetails,Index,show_cart,add_to_cart,remove_from_cart,update_cart_item,CheckoutList,order_success
from .views import unlike

urlpatterns = [
    path('home/',home, name="home"),
    path('<pk>/details/',ProdectDetails.as_view(),name="items_details"),
    path('',Index.as_view(),name="index"),
    path('cart/',show_cart,name="cart"),
    path('add_to_cart/',add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/',remove_from_cart, name='remove_from_cart'),
    path('update_cart_item/<int:item_id>/', update_cart_item, name='update_cart_item'),
    path('checkout/',CheckoutList.as_view(), name='checkout'),
    path('order_success/',order_success,name='order_success'),
    path('<int:pid>/unlike/',unlike.as_view(),name="unlike")
    
]
