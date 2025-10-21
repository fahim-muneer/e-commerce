from django.urls import path,include
from .views import paymenthandler
from django.contrib.auth.decorators import login_required
urlpatterns =[
        
        path('checkout/paymenthandler/', login_required(paymenthandler), name='save_payment'),

]
