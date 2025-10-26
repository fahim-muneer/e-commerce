from django.urls import path,include
from .views import home,ProdectDetails,Index,show_cart,add_to_cart,remove_from_cart,update_cart_item,CheckoutList,order_success
from .views import unlike,about,contact_us,add_review
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('home/',home, name="home"),
    path('<pk>/details/',ProdectDetails.as_view(),name="items_details"),
    path('',Index.as_view(),name="index"),
    path('cart/',login_required(show_cart),name="cart"),
    path('add_to_cart/',login_required(add_to_cart), name='add_to_cart'),
    path('remove_from_cart/<int:item_id>/',login_required(remove_from_cart), name='remove_from_cart'),
    path('update-cart-item/<int:item_id>/', login_required(update_cart_item), name='update_cart_item'), 
    path('checkout/',login_required(CheckoutList.as_view()), name='checkout'),
    path('<int:uid>/order_success/',login_required(order_success),name='order_success'),
    path('<int:pid>/unlike/',login_required(unlike.as_view()),name="unlike"),
    path('about/',about,name="about"),
    path('contact_us/',contact_us,name="contact_us"),
    path('add-review/<int:variant_id>/',add_review, name='add_review'),


    
]
