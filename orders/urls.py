from django.urls import path,include
from . views import OrderListView,OrderDetails,UserOrderListView,UserOrderDetailView,OrderAddressAdd,OrderAddressView,EditOrderAddress
from .views import pdf,return_reason,ReturSuccess

urlpatterns = [
    
    path('order_list/',OrderListView.as_view(),name="order_list"),
    path('<pk>/order_details/',OrderDetails.as_view(),name='order_details'),
    path('user_order_list/',UserOrderListView.as_view(),name="user_order_list"),
    path('<int:pk>/user_order_details/',UserOrderDetailView.as_view(),name="user_order_details"),
    path('add_order_address/',OrderAddressAdd.as_view(),name="add_order_address"),
    path('order_address_view/',OrderAddressView.as_view(),name="order_address_view"),
    path('<pk>/edit_order_address/',EditOrderAddress.as_view(),name="edit_order_address"),
    path('order/<int:uid>/download-pdf/', pdf, name="download_pdf"),
    path('<int:uid>/return_reason/',return_reason,name="return_reason"),
    path('cancel-success/',ReturSuccess.as_view(),name="cancel_success")
    
]
