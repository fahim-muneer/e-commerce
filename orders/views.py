from django.shortcuts import render
from .models import OrderAddress,Orders
from customer.models import UserAddress

# Create your views here.

def CreateOrder(request ,address_id ):
    user = request.user
    selected_address = UserAddress.objects.get(id=address_id , user = user) #pylint: disable=no-member
    order_address = OrderAddress.objects.create(                            #pylint: disable=no-member
    mobile     =  selected_address.mobile,
    second_mob =  selected_address.second_mob,
    address    = selected_address.address,
    city       =  selected_address.city,
    state      =  selected_address.state,
    pin        =  selected_address.pin,
    country    = selected_address.country
    )
        
    order = Orders.objects.create(          #pylint: disable=no-member
        user =user,
        order_address =order_address
    )
    
    return order 