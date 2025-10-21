from django.urls import path
# from . views import OrderListView,OrderDetails,UserOrderListView,UserOrderDetailView,OrderAddressAdd,OrderAddressView
from . views import (
    OrderListView, OrderDetails, UserOrderListView, UserOrderDetailView,
    OrderAddressAdd, OrderAddressView,EditOrderAddress,OrderCancellSuccess,ReturnSuccess
)
from .views import (
    pdf, cancel_item, return_item, cancel_entire_order, return_entire_order,
    cancel_return_request, cancel_return_request_order,
    approve_return_admin, reject_return_admin, complete_return_admin
)
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # ============ ADMIN URLS ============
    path('order_list/', staff_member_required(OrderListView.as_view()), name="order_list"),
    path('<int:pk>/order_details/', staff_member_required(OrderDetails.as_view()), name='order_details'),
    
    # Admin: Return Management
    path('admin/return/approve/<int:order_id>/<int:item_id>/',staff_member_required(approve_return_admin), name='approve_return_item'),
    path('admin/return/reject/<int:order_id>/<int:item_id>/', staff_member_required(reject_return_admin), name='reject_return_item'),
    path('admin/return/complete/<int:order_id>/<int:item_id>/',staff_member_required(complete_return_admin), name='complete_return_item'),
    
    
    path('user_order_list/', login_required(UserOrderListView.as_view()), name="user_order_list"),
    path('<int:pk>/user_order_details/', login_required(UserOrderDetailView.as_view()), name="user_order_details"),
    
    
    path('add_order_address/', login_required(OrderAddressAdd.as_view()), name="add_order_address"),
    path('order_address_view/', login_required(OrderAddressView.as_view()), name="order_address_view"),
    path('<int:pk>/edit_order_address/', login_required(EditOrderAddress.as_view()), name="edit_order_address"),
    
    
    # ============ PDF GENERATION ============
    path('order/<int:uid>/download-pdf/', pdf, name="download_pdf"),
    
    
    # ============ CANCEL OPERATIONS (Before Delivery) ============
    # Cancel individual item
    path('<int:oid>/<int:pid>/cancel_item/', login_required(cancel_item), name="cancel_item"),
    
    # Cancel entire order - show reason form
    path('<int:oid>/cancel_order_reason/', login_required(cancel_entire_order), name="cancel_order_reason"),
    
    # Cancel success page
    path('cancel-success/', login_required(OrderCancellSuccess.as_view()), name="cancel_success"),
    
    
    # ============ RETURN OPERATIONS (After Delivery) ============
    # Return individual item - show return form
    path('<int:order_id>/<int:item_id>/return_item/', login_required(return_item), name="return_item"),
    
    # Return entire order - show reason form
    path('<int:uid>/return_order_reason/', login_required(return_entire_order), name="return_order_reason"),
    
    # Return success page
    path('return_success/', login_required(ReturnSuccess.as_view()), name="return_success"),
    
    
    # ============ CANCEL RETURN REQUEST (User Changes Mind) ============
    # Cancel return request for individual item
    path('<int:order_id>/<int:item_id>/cancel_return_request/', login_required(cancel_return_request), name="cancel_return_request"),
    
    # Cancel return request for entire order
    path('<int:uid>/cancel_return_request_order/', login_required(cancel_return_request_order), name="cancel_return_request_order"),
]
    
    
