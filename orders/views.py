from .models import OrderAddress,Orders,Cart,OrderItem
from customer.models import UserAddress
from django.views.generic import DetailView ,ListView , UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from .forms import OrderAddressForm,ItemCancellReason
from django.db import transaction
from django.views import View
from django.contrib import messages
from django.shortcuts import redirect,render,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from customer.models import Register,Customer
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from django.http import FileResponse
import io
from custom_admin.views import AdminLoginMixin
from customer.views import MyLoginRequiredMixin
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from django.db.models import F
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Orders, OrderItem
from django.http import HttpResponseForbidden
from decimal import Decimal




def pdf(request, uid):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    order = Orders.objects.get(id=uid)    # pylint: disable=no-member
    items = OrderItem.objects.filter(order_id=order.id)   # pylint: disable=no-member
    story.append(Paragraph("<b><font size=17>BANUS FURNITUR</font></b>", styles['Title']))

    story.append(Paragraph("<b><font size=14>Invoice</font></b>", styles['Title']))
    
    
    story.append(Spacer(1, 12))    
    story.append(Paragraph(f"<b>Customer:</b> {order.user.full_name}", styles['Normal'])) 
    story.append(Paragraph(f"<b>Order ID:</b> {order.order_Id}", styles['Normal']))
    story.append(Paragraph(f"<b>Mobile:</b> {order.delivery_address.mobile}", styles['Normal']))
    story.append(Paragraph(f"<b>second:</b> {order.delivery_address.second_mob}", styles['Normal']))
    story.append(Paragraph(f"<b>Address:</b> {order.delivery_address.address}", styles['Normal']))  
    story.append(Paragraph(f"<b>District:</b> {order.delivery_address.city}", styles['Normal']))
    story.append(Paragraph(f"<b>Pin:</b> {order.delivery_address.pin}", styles['Normal']))
    story.append(Paragraph(f"<b>State:</b> {order.delivery_address.state}", styles['Normal']))

    
    
    story.append(Paragraph(f"<b>Payment Method:</b> {order.get_payment_method_display()}", styles['Normal']))
    story.append(Spacer(1, 12))

    
    data = [["Product", "Price", "Quantity", "Total"]]

    grand_total = 0
    for item in items:
        total = item.unit_price * item.quantity
        grand_total += total
        data.append([
            item.product.name,
            f"{item.unit_price}",
            str(item.quantity),
            f"{total}"
        ])

    
    data.append(["", "", "Grand Total", f"{grand_total}"])

    table = Table(data, colWidths=[200, 80, 80, 100])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"Order_{order.id}.pdf")


def CreateOrder(request ,address_id ):
    user = request.user
    selected_address = UserAddress.objects.get(id=address_id , user = user) #pylint: disable=no-member
    order_address = OrderAddress.objects.create(                            #pylint: disable=no-member
    mobile    =  selected_address.mobile,
    second_mob =  selected_address.second_mob,
    address    = selected_address.address,
    city     =  selected_address.city,
    state    =  selected_address.state,
    pin     =  selected_address.pin,
    )
        
    order = Orders.objects.create(          #pylint: disable=no-member
        user =user,
        delivery_address = order_address
    )
    
    return order 




@method_decorator(never_cache, name='dispatch')
class OrderListView(AdminLoginMixin, ListView):
    model = Orders
    template_name = 'orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 5
    
    def get_queryset(self):
        queryset = Orders.objects.all().prefetch_related("items__product").order_by("-created_at")
        order_id = self.request.GET.get('order_id')
        status = self.request.GET.get('order_status')

        if order_id and status:
            try:
                order = Orders.objects.get(id=order_id)
                status_int = int(status)
                order.order_status = status_int

                fields_to_update = ["order_status"]

                if status_int == 3 and not order.delivered_at:
                    order.delivered_at = timezone.now()
                    fields_to_update.append("delivered_at")

                order.save(update_fields=fields_to_update)
                messages.success(self.request, f"Order #{order.id} status updated successfully.")
            except Orders.DoesNotExist:
                messages.error(self.request, "Order not found.")
            except ValueError:
                messages.error(self.request, "Invalid status value.")

        
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
        context['status_choices'] = Orders.STATUS_CHOICES  
        return context
    
    
@method_decorator(never_cache, name='dispatch')
class OrderDetails(DetailView):
    model = Orders
    context_object_name = 'order'
    template_name = 'orders/order_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        context['order_items'] = order.items.select_related('product').all()
        return context

    def get(self, request, *args, **kwargs):
        order = self.get_object()

        item_id = request.GET.get('item_id')
        new_status = request.GET.get('status')

        if item_id and new_status:
            try:
                item = order.items.get(id=item_id)

                if item.order_status == 3:  # Dlvrd
                    messages.warning(request, f"{item.product.name} is already delivered. Status cannot be changed.")
                else:
                   
                    if item.order_status in [1, 2] and int(new_status) in [3, 4]:
                        item.order_status = int(new_status)
                        item.save()
                        messages.success(request, f"Status updated for {item.product.name}.")
                    else:
                        messages.warning(request, "Invalid status change.")

            except OrderItem.DoesNotExist:
                messages.error(request, "Order item not found.")

            return redirect('order_details', pk=order.pk)

        return super().get(request, *args, **kwargs)




@method_decorator(never_cache, name='dispatch')   
class UserOrderListView(MyLoginRequiredMixin, ListView):
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



@method_decorator(never_cache, name='dispatch')
class UserOrderDetailView(MyLoginRequiredMixin, DetailView):
    model = Orders
    context_object_name = 'order'
    template_name = 'orders/user_order_details.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()
        
        context['profile'] = Customer.objects.get(user=self.request.user)
        
        context['can_return'] = order.can_return
        context['days_left'] = order.days_left_for_return
        
        active_total = Decimal('0.00')
        cancelled_returned_total = Decimal('0.00')
        
        for item in order.items.all():
            item_total = item.unit_price * item.quantity
            if item.order_status in [4, 7]:  
                cancelled_returned_total += item_total
            else:
                active_total += item_total
        
        context['active_items_total'] = active_total
        context['cancelled_returned_total'] = cancelled_returned_total
        context['original_total'] = active_total + cancelled_returned_total
        
        return context
    
    

@method_decorator(never_cache, name='dispatch')
class OrderAddressView(MyLoginRequiredMixin,View):
    def get(self , request):
        address=OrderAddress.objects.all() #pylint: disable=no-member
        context={
            'address':address
        }
        return render(request , '',context)

@method_decorator(never_cache, name='dispatch')
class OrderAddressAdd(MyLoginRequiredMixin,View):
    
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
  
  
  
@method_decorator(never_cache, name='dispatch')
class OrderCancellSuccess(MyLoginRequiredMixin, View):
    def get(self , request):
        return render(request,'orders/cancel_success.html')
        
        
        
@method_decorator(never_cache, name='dispatch')          
class EditOrderAddress(MyLoginRequiredMixin,UpdateView):
    model=OrderAddress
    fields=['mobile','second_mob','address','city','state','pin','country',]
    template_name='orders/edit_order_address.html'
    success_url=reverse_lazy('checkout')
  
  
@method_decorator(never_cache, name='dispatch')
class ReturnSuccess(MyLoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'orders/cancel_success.html')
    
    
@login_required
def cancel_item(request, oid, pid):

    order = get_object_or_404(Orders, id=oid, user=request.user)
    item = get_object_or_404(OrderItem, id=pid, order=oid)

    if item.order_status not in [1, 2]:
        messages.error(request, f"Item '{item.product.name}' cannot be cancelled at this stage.")
        return redirect('user_order_details', pk=oid)

    if request.method == 'POST':
        reason = request.POST.get("reason")
        if not reason:
            context = {
                "oid": oid,
                "order_Id": order.order_Id,
                "item_amount": item.total_price,
                "payment": order.payment_status
            }
            return render(request, 'orders/item_cancel_reason.html', context)

        try:
            with transaction.atomic():
                print("=" * 60)
                print(" CANCEL ITEM - START")
                print("=" * 60)
                
                original_order_total = Decimal(str(order.total_amount))
                print(f"Original order total (paid): ₹{original_order_total}")
                
                item_total = Decimal(str(item.total_price))
                print(f" Cancelling: {item.product.name}")
                print(f"   Item price: ₹{item_total}")
                print(f"   Quantity: {item.quantity}")
                
                had_coupon = bool(order.coupon_code)
                coupon_value = Decimal('0')
                coupon_min = Decimal('0')
                
                if had_coupon:
                    coupon = order.coupon_code
                    coupon_value = Decimal(str(coupon.discount_value))
                    coupon_min = Decimal(str(coupon.min_cart_value))
                    print(f"  Coupon: {coupon.coupon_code}")
                    print(f"   Discount: ₹{coupon_value}")
                    print(f"   Minimum: ₹{coupon_min}")
                
                item.order_status = 4
                item.item_cancel_reason = reason
                item.save(update_fields=['order_status', 'item_cancel_reason'])
                print("Item marked as cancelled")

                if item.variant:
                    item.variant.stock = F('stock') + item.quantity
                    item.variant.save(update_fields=['stock'])
                    item.variant.refresh_from_db()
                    print(f"   Restored {item.quantity} units to variant stock")
                else:
                    item.product.stock = F('stock') + item.quantity
                    item.product.save(update_fields=['stock'])
                    item.product.refresh_from_db()
                    print(f"   Restored {item.quantity} units to product stock")

                remaining_items = order.items.exclude(order_status__in=[4, 7])
                remaining_count = remaining_items.count()
                remaining_subtotal = sum(Decimal(str(i.total_price)) for i in remaining_items)
                
                print(f" After cancellation:")
                print(f"   Remaining items: {remaining_count}")
                print(f"   Remaining subtotal: ₹{remaining_subtotal}")
                
                refund_amount = Decimal('0')
                new_order_total = Decimal('0')
                coupon_removed = False
                
                if remaining_count == 0:
                    print("\nNo items remaining - full refund")
                    refund_amount = original_order_total
                    new_order_total = Decimal('0')
                    coupon_removed = True
                    order.order_status = 4
                    order.coupon_code = None
                    
                elif had_coupon:
                    if remaining_subtotal < coupon_min:
                        print(f"\n Remaining (₹{remaining_subtotal}) < minimum (₹{coupon_min})")
                        print("   Coupon becomes INVALID")
                        
                      
                        new_order_total = remaining_subtotal
                        
                        refund_amount = original_order_total - new_order_total
                        
                        print(f"   New order total (no coupon): ₹{new_order_total}")
                        print(f"   Refund: ₹{original_order_total} - ₹{new_order_total} = ₹{refund_amount}")
                        
                        order.coupon_code = None
                        coupon_removed = True
                        
                        messages.info(
                            request,
                            f"Coupon '{coupon.coupon_code}' removed (order below minimum). "
                            f"₹{coupon_value} discount no longer applied."
                        )
                    else:
                        print(f"\n  Remaining (₹{remaining_subtotal}) >= minimum (₹{coupon_min})")
                        print("   Coupon remains VALID")
                        
                        new_order_total = remaining_subtotal - coupon_value
                        
                        refund_amount = original_order_total - new_order_total
                        
                        print(f"   New order total (with coupon): ₹{new_order_total}")
                        print(f"   Refund: ₹{original_order_total} - ₹{new_order_total} = ₹{refund_amount}")
                else:
                    print("\n No coupon on order")
                    new_order_total = remaining_subtotal
                    refund_amount = item_total
                    print(f"   New order total: ₹{new_order_total}")
                    print(f"   Refund (item price): ₹{refund_amount}")
                
                if refund_amount < Decimal('0'):
                    print(" Refund was negative, setting to 0")
                    refund_amount = Decimal('0')
                
                order.total_amount = new_order_total
                order.save(update_fields=['total_amount', 'order_status', 'coupon_code'])
                print(f"\n Order updated:")
                print(f"   New total: ₹{order.total_amount}")
                print(f"   Status: {order.get_order_status_display()}")
                
                if order.payment_status == Orders.PAYMENT_PAID and refund_amount > 0:
                    from wallet.models import Wallet, WalletTransaction
                    
                    wallet, _ = Wallet.objects.get_or_create(user=request.user)
                    
                    print(f"\n  Processing refund to wallet: ₹{refund_amount}")
                    
                    wallet.add_money(
                        amount=refund_amount,
                        transaction_type=WalletTransaction.CREDIT_REFUND,
                        description=f"Refund for cancelled item from Order #{order.order_Id}",
                        reference_id=str(order.id)
                    )
                    
                    messages.success(
                        request,
                        f"Item '{item.product.name}' cancelled. ₹{refund_amount} refunded to your wallet."
                    )
                    print("  Refund completed")
                else:
                    messages.success(request, f"Item '{item.product.name}' cancelled. Stock restored.")
                    print("  Cancellation completed (no refund needed)")
                
                print("=" * 60)
                print("🛒 CANCEL ITEM - END")
                print("=" * 60)

        except Exception as e:
            print(f"\n  ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error cancelling item: {str(e)}')

    return redirect('user_order_details', pk=oid)


@login_required
def cancel_entire_order(request, oid):
    '''to cacell all items at one click ,refund and restock '''
    order = get_object_or_404(Orders, id=oid, user=request.user)

    if order.order_status not in [1, 2]:  
        messages.error(request, 'Order cannot be cancelled at this stage.')
        return redirect('user_order_details', pk=oid)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        if not reason or len(reason) < 20:
            messages.error(request, 'Please provide a detailed reason (minimum 20 characters).')
            return render(request, 'orders/cancel_reason.html', {'order': order})

        try:
            with transaction.atomic():
                original_total = order.total_amount
                refund_amount = Decimal('0.00')

              
                for item in order.items.exclude(order_status__in=[4, 7]):
                    if item.variant:
                        item.variant.stock = F('stock') + item.quantity
                        item.variant.save(update_fields=['stock'])
                    else:
                        item.product.stock = F('stock') + item.quantity
                        item.product.save(update_fields=['stock'])

                    item.order_status = 4  
                    item.item_cancel_reason = reason
                    item.save(update_fields=['order_status', 'item_cancel_reason'])

                if order.coupon_code:
                    coupon = order.coupon_code
                    coupon_discount = Decimal(str(coupon.discount_value))
                    print(f"Coupon applied: {coupon.coupon_code}, Discount: ₹{coupon_discount}")

                    refund_amount = original_total  
                                                       

                    # coupon.use_limit = F('use_limit') + 1
                    # coupon.save(update_fields=['use_limit'])

                    order.coupon_code = None
                else:
                    refund_amount = original_total

                order.order_status = 4
                order.return_reason = reason
                order.total_amount = Decimal('0.00')
                order.save(update_fields=['order_status', 'return_reason', 'coupon_code', 'total_amount'])

                if order.payment_status == Orders.PAYMENT_PAID and refund_amount > 0:
                    from wallet.models import Wallet, WalletTransaction

                    wallet, _ = Wallet.objects.get_or_create(user=request.user)
                    wallet.add_money(
                        amount=refund_amount,
                        transaction_type=WalletTransaction.CREDIT_REFUND,
                        description=f"Refund for cancelled Order #{order.order_Id}",
                        reference_id=str(order.id)
                    )

                    messages.success(
                        request,
                        f'Order cancelled successfully. ₹{refund_amount} refunded to your wallet (after coupon adjustment).'
                    )
                else:
                    messages.success(request, 'Order cancelled successfully. Stock restored.')

                return redirect("cancel_success")

        except Exception as e:
            messages.error(request, f'Error cancelling order: {str(e)}')
            return render(request, 'orders/cancel_reason.html', {'order': order})

    return render(request, 'orders/cancel_reason.html', {'order': order})


@login_required
def return_item(request, order_id, item_id):
    order = get_object_or_404(Orders, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    if item.order_status != 3:
        messages.error(request, "Only delivered items can be returned.")
        return redirect('user_order_details', pk=order_id)
   
    if request.method == 'POST':
        return_reason = request.POST.get('return_reason', '').strip()
        
        if not return_reason:
            messages.error(request, "Please provide a reason for return.")
            return render(request, 'orders/return_item_form.html', {
                'order': order,
                'item': item,
                # 'days_left': (return_deadline - timezone.now()).days + 1
            })
        
        item.order_status = 5  
        item.return_reason = return_reason
        item.save()
        
        
        messages.success(request, f"Return request for '{item.product.name}' submitted. Awaiting approval.")
        return redirect('user_order_details', pk=order_id)
    
    return render(request, 'orders/return_item_form.html', {
        'order': order,
        'item': item,
        # 'days_left': days_left
    })


@login_required
def approve_return_admin(request, order_id, item_id):
    order = get_object_or_404(Orders, id=order_id)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    if item.order_status != 5: 
        messages.error(request, "Invalid return status.")
        return redirect('order_details', pk=order_id)
    
   
    item.order_status = 6 
    
    
    item.save()
    
    
    
    messages.success(request, f"Return approved for '{item.product.name}'. Arrange pickup.")
    return redirect('order_details', pk=order_id)




@login_required
def complete_return_admin(request, order_id, item_id):

    order = get_object_or_404(Orders, id=order_id)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if item.order_status != 6:  
        messages.error(request, "Invalid return status.")
        return redirect('order_details', pk=order_id)

    try:
        with transaction.atomic():
            print("=" * 60)
            print(" COMPLETE RETURN (ADMIN) - START")
            print("=" * 60)

            original_order_total = Decimal(str(order.total_amount))
            item_total = Decimal(str(item.total_price))
            print(f"Original order total: ₹{original_order_total}")
            print(f"Returning item #{item.id}: ₹{item_total}")

            if item.variant:
                item.variant.stock = F('stock') + item.quantity
                item.variant.save(update_fields=['stock'])
                item.variant.refresh_from_db()
                print(f"Restored {item.quantity} units to variant stock.")
            else:
                item.product.stock = F('stock') + item.quantity
                item.product.save(update_fields=['stock'])
                item.product.refresh_from_db()
                print(f"Restored {item.quantity} units to product stock.")

           
            item.order_status = 7  
            item.save(update_fields=['order_status'])
            print("Item marked as returned.")

            
            remaining_items = order.items.exclude(order_status__in=[4, 7])
            remaining_subtotal = sum(Decimal(str(i.total_price)) for i in remaining_items)
            remaining_count = remaining_items.count()

            print(f" Remaining items: {remaining_count}")
            print(f"   Remaining subtotal: ₹{remaining_subtotal}")

            refund_amount = Decimal('0')
            new_order_total = Decimal('0')
            coupon_removed = False

            had_coupon = bool(order.coupon_code)
            coupon_value = Decimal('0')
            coupon_min = Decimal('0')

            if had_coupon:
                coupon = order.coupon_code
                coupon_value = Decimal(str(coupon.discount_value))
                coupon_min = Decimal(str(coupon.min_cart_value))
                print(f" Coupon details:")
                print(f" - Code: {coupon.coupon_code}")
                print(f" - Discount: ₹{coupon_value}")
                print(f" - Minimum: ₹{coupon_min}")

            if remaining_count == 0:
                refund_amount = original_order_total
                new_order_total = Decimal('0')
                order.order_status = 7
                order.coupon_code = None

            elif had_coupon:
                if remaining_subtotal < coupon_min:
                    print(" Remaining total below coupon minimum → Coupon invalid.")
                    new_order_total = remaining_subtotal
                    refund_amount = original_order_total - new_order_total

                    coupon_code_str = coupon.coupon_code
                    order.coupon_code = None
                    coupon_removed = True

                    print(f"New order total (no coupon): ₹{new_order_total}")
                    print(f"Refund = ₹{original_order_total} - ₹{new_order_total} = ₹{refund_amount}")

                    messages.info(
                        request,
                        f"Coupon '{coupon_code_str}' removed (order below minimum). "
                        f"Refund reduced by ₹{coupon_value}."
                    )
                else:
                    print(" Coupon remains valid after return.")
                    new_order_total = remaining_subtotal - coupon_value
                    refund_amount = original_order_total - new_order_total
                    print(f"New order total (with coupon): ₹{new_order_total}")
                    print(f"Refund = ₹{original_order_total} - ₹{new_order_total} = ₹{refund_amount}")

            else:
                print("No coupon applied.")
                new_order_total = remaining_subtotal
                refund_amount = item_total
                print(f"Refund (item price): ₹{refund_amount}")

            if refund_amount < Decimal('0'):
                print("Refund was negative, setting to 0.")
                refund_amount = Decimal('0')

            order.total_amount = new_order_total
            order.save(update_fields=['total_amount', 'order_status', 'coupon_code'])
            print(f"\nOrder updated:")
            print(f" - New total: ₹{order.total_amount}")
            print(f" - Status: {order.get_order_status_display()}")

            if order.payment_status == Orders.PAYMENT_PAID and refund_amount > 0:
                from wallet.models import Wallet, WalletTransaction
                wallet, _ = Wallet.objects.get_or_create(user=order.user)

                print(f" Refunding ₹{refund_amount} to user's wallet.")
                wallet.add_money(
                    amount=refund_amount,
                    transaction_type=WalletTransaction.CREDIT_REFUND,
                    description=f"Refund for returned item from Order #{order.order_Id}",
                    reference_id=str(order.id)
                )

                messages.success(
                    request,
                    f"Return completed. ₹{refund_amount} refunded to customer's wallet "
                    f"{'(after coupon adjustment)' if coupon_removed else ''}."
                )
            else:
                messages.success(request, "Return completed. Stock restored successfully.")

            print("=" * 60)
            print(" COMPLETE RETURN (ADMIN) - END")
            print("=" * 60)

    except Exception as e:
        messages.error(request, f"Error completing return: {str(e)}")
        print(f" Error completing return: {str(e)}")

    return redirect('order_details', pk=order_id)

@login_required
def cancel_return_request(request, order_id, item_id):
    """Customer cancels their return request (no stock changes)"""
    order = get_object_or_404(Orders, id=order_id, user=request.user)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    if item.order_status != 5:  
        messages.error(request, 'Cannot cancel this return request.')
        return redirect('user_order_details', pk=order_id)
    
    if request.method == 'POST':
        item.order_status = 3
        item.return_reason = None
        item.save()
        
        
        messages.success(request, 'Return request cancelled successfully.')
    
    return redirect('user_order_details', pk=order_id)


@login_required
def cancel_return_request_order(request, uid):
    """Customer cancels return request for entire order"""
    order = get_object_or_404(Orders, id=uid, user=request.user)
    
    if order.order_status != 5:
        messages.error(request, 'Cannot cancel this return request.')
        return redirect('user_order_details', pk=uid)
    
    if request.method == 'POST':
        order.order_status = 3  
        order.product_return_reason = None
        order.return_requested_at = None
        order.save()
        
        order.items.filter(order_status=5).update(
            order_status=3,
            return_reason=None
        )
        
        messages.success(request, 'Return request cancelled successfully.')
    
    return redirect('user_order_details', pk=uid)

@login_required
def return_entire_order(request, uid):
    """Request return for entire delivered order"""
    order = get_object_or_404(Orders, id=uid, user=request.user)
    
    if not order.can_return:
        messages.error(request, 'This order is not eligible for return.')
        return redirect('user_order_details', pk=uid)
    
    if order.order_status >= 5:
        messages.warning(request, 'A return request has already been submitted.')
        return redirect('user_order_details', pk=uid)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason or len(reason) < 20:
            messages.error(request, 'Please provide a detailed reason (minimum 20 characters).')
            return render(request, 'orders/return_reason.html', {
                'order': order,
                'days_left': order.days_left_for_return  
            })
        
        try:
            with transaction.atomic():
                order.order_status = 5
                order.product_return_reason = reason
                order.return_requested_at = timezone.now()
                order.save()
                
                order.items.filter(order_status=3).update(
                    order_status=5,
                    return_reason=reason
                )
                
                
                messages.success(request, 'Return request submitted. Awaiting approval.')
                return redirect('return_success')
                
        except Exception as e:
            messages.error(request, f'Error submitting return: {str(e)}')
            return render(request, 'orders/return_reason.html', {
                'order': order,
                'days_left': order.days_left_for_return
            })
    
    return render(request, 'orders/return_reason.html', {
        'order': order,
        'days_left': order.days_left_for_return  
    })

@login_required  
def reject_return_admin(request, order_id, item_id):
    """ADMIN: Reject return request"""
    order = get_object_or_404(Orders, id=order_id)
    item = get_object_or_404(OrderItem, id=item_id, order=order)
    
    if item.order_status != 5:
        messages.error(request, "Invalid return status.")
        return redirect('order_details', pk=order_id)
    
    item.order_status = 3
    item.return_reason = None
    item.save()
    
    messages.success(request, f"Return rejected for '{item.product.name}'.")
    return redirect('order_details', pk=order_id)
