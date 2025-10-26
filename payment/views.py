
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseBadRequest
from orders.models import Orders, OrderItem
from products.models import ProductVariants, ProductPage
from django.db.models import F
from django.db import transaction
import razorpay
from django.conf import settings
from customer.utils import mark_referral_first_purchase
from django.urls import reverse


@csrf_exempt
def paymenthandler(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            
            order = Orders.objects.get(razorpay_order_id=razorpay_order_id)
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            result = razorpay_client.utility.verify_payment_signature(params_dict)

            if result is not None:
                with transaction.atomic():
                    order.payment_status = Orders.PAID
                    order.order_status = Orders.CONFIRMED
                    order.save()
                    
                    for order_item in order.items.all():
                        if order_item.variant:
                            order_item.variant.stock = F('stock') - order_item.quantity
                            order_item.variant.save(update_fields=["stock"])
                        else:
                            order_item.product.stock = F('stock') - order_item.quantity
                            order_item.product.save(update_fields=["stock"])
                            
                    cart = order.user.cart
                    cart.delete()
                    
                    mark_referral_first_purchase(order.user)

                    return JsonResponse({'success': True, 'redirect_url': reverse('order_success', args=[order.pk])})
            else:
                return JsonResponse({'success': False, 'error': 'Signature verification failed'})
        except Orders.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Order not found.'})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)})

    return HttpResponseBadRequest()