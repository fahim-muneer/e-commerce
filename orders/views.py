from .models import OrderAddress,Orders,Cart,OrderItem
from customer.models import UserAddress
from django.views.generic import DetailView ,ListView , UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .forms import OrderAddressForm
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect,render,get_object_or_404
from django.urls import reverse_lazy
from customer.models import Register,Customer
from django.core.paginator import Paginator
import reportlab
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas 
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate,Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def pdf(request,uid):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles =getSampleStyleSheet()
    story = []
    order=Orders.objects.get(id= uid)   #pylint: disable=no-member
    items= OrderItem.objects.filter(order_id=order.id)   #pylint: disable=no-member
    story.append(Paragraph(f"<b>Order ID:</b> {order.id}", styles['Normal']))
    story.append(Paragraph(f"<b>Address:</b> {order.delivery_address}", styles['Normal']))
    story.append(Paragraph(f"<b>Payment Method:</b> {order.get_payment_method_display()}", styles['Normal']))
    

    for item in items:
        story.append(Paragraph(f"<b>Product:</b> {item.product.name}", styles['Normal']))
        story.append(Paragraph(f"<b>Price:</b> {item.unit_price}", styles['Normal']))
        story.append(Paragraph(f"<b>Quantity:</b> {item.quantity}", styles['Normal']))
        story.append(Paragraph(f"<b>Total Price:</b> {item.total_price}", styles['Normal']))  
    doc.build(story)   
    buffer.seek(0)
    return FileResponse(buffer , as_attachment=True , filename=f"Order_{order.id}.pdf")

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
        delivery_address = order_address
    )
    
    return order 





class OrderListView(LoginRequiredMixin, ListView):
    model = Orders
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 5
    
    def get_queryset(self):
        queryset = Orders.objects.all().prefetch_related("items__product").order_by("-created_at") #pylint: disable=no-member
        order_id = self.request.GET.get('order_id')
        status = self.request.GET.get('order_status')

        if order_id and status:
            try:
                order = Orders.objects.get(id=order_id)  #pylint: disable=no-member
                order.order_status = int(status)            
                order.save(update_fields=["order_status"])
            except (Orders.DoesNotExist, ValueError):               #pylint: disable=no-member
                pass         
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__full_name__icontains=search) | Q(user__email__icontains=search)
            )

        status_filter = self.request.GET.get('status')
        if status_filter:
            try:
                queryset = queryset.filter(order_status=int(status_filter))
            except (ValueError, TypeError):
                pass

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['status_choices'] = Cart.STATUS_CHOICE
        return context
    

class OrderDetails(LoginRequiredMixin, DetailView):
    model = Orders
    context_object_name = 'order'
    template_name = 'orders/order_details.html'
    
    def get_queryset(self):
        return Cart.objects.filter(       #pylint: disable=no-member
            owner=self.request.user, 
            order_status__gt=Cart.CART_STAGE
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        context['cart_items'] = order.ordered_items.select_related('product').all()
        
        context['subtotal'] = order.total_price
        context['shipping_cost'] = 0
        context['total'] = context['subtotal'] + context['shipping_cost']
        
        context['customer'] = order.owner
        
        return context
    
class UserOrderListView(LoginRequiredMixin, ListView):
    model = Orders
    template_name = 'orders/user_order_list.html'
    context_object_name = 'orders'
    paginate_by = 5
    
    
    def get_queryset(self):
        return Orders.objects.filter(user=self.request.user).prefetch_related("items__product").order_by("-created_at")     # pylint: disable=no-member
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = Customer.objects.get(user=self.request.user)  # pylint: disable=no-member
        context['total_orders'] = Orders.objects.filter(user=self.request.user).count()         # pylint: disable=no-member
        return context




class UserOrderDetailView(LoginRequiredMixin, DetailView):
    model = Orders
    context_object_name = 'order'
    template_name = 'orders/user_order_details.html'
    
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['profile'] = Customer.objects.get(user=self.request.user)   #pylint: disable=no-member
        return context
    
    


class OrderAddressView(View):
    def get(self , request):
        address=OrderAddress.objects.all() #pylint: disable=no-member
        context={
            'address':address
        }
        return render(request , '',context)


class OrderAddressAdd(View):
    
    def get(self,request):
        form=OrderAddressForm()
        return render(request,'orders/add_order_address.html',{'form':form})
    
    
   
    def post(self, request):
        form=OrderAddressForm(request.POST)
        if form.is_valid():
            address=form.save(commit=False)
            try:
                register_user=Register.objects.get(email=request.user.email)
                address.user=register_user
            except Register.DoesNotExist:  #pylint: disable=no-member
                messages.error(request,'The user is not exist.')
                return render(request,'orders/add_order_address.html',{'form':form})
            address.save()
            messages.success(request,'Your order Address was added successfully.')
            return redirect('checkout')
        else:
            messages.error(request,'Cjeck your credentials and try again.')
            return render(request,'orders/add_order_address.html',{'form':form})
            
class EditOrderAddress(UpdateView):
    model=OrderAddress
    fields=['mobile','second_mob','address','city','state','pin','country',]
    template_name='orders/edit_order_address.html'
    success_url=reverse_lazy('checkout')

    

def return_reason(request , uid):
    
    
    order = get_object_or_404(Orders, id=uid)    #pylint: disable=no-member
    
    if request.method == 'POST':    
        
        reasons=request.POST.get('reason')
        
        if reasons:            
            order.order_status=4
            order.return_reason=reasons
            order.save()
            messages.success(request,'Your reason sent successfully.')
            return redirect("cancel_success")
        else:
            messages.error(request,'Please fill your reason.')
            return render(request,'orders/return_reason.html',{"order":order})     
        
        
    
    return render(request,'orders/return_reason.html',{'order':order})

class ReturSuccess(View):
    def get(self , request):
        return render(request,'orders/cancel_success.html')