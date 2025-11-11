from django.shortcuts import redirect, render, HttpResponseRedirect, get_object_or_404
from coupon.models import CouponUsage
from products.models import ProductPage
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.views.generic import DetailView, View
from category.models import CategoryPage
from orders.models import Cart, CartItems, OrderAddress, Orders, OrderItem
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from wish_list.models import WishListItems
User = get_user_model()
from django.urls import reverse
from .forms import VarientSelectforms
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from customer.views import MyLoginRequiredMixin
from decimal import Decimal
from products.models import ProductVariants,Review
from django.db.models import Prefetch
from django.views.decorators.http import require_POST
from customer.utils import mark_referral_first_purchase
from django.conf import settings
from django.utils import timezone
import logging
import razorpay
from decimal import Decimal
from django.utils import timezone
from django.contrib import messages
from coupon.models import Coupons,CouponUsage
logger = logging.getLogger(__name__)
from wallet.models import Wallet
from django.db.models import Q
from products.forms import ReviewForm
from banner.models import Banner

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class Index(View):
    def get(self, request):
        latest_products = ProductPage.objects.order_by('-pk')[:5]
        featured_product = ProductPage.objects.order_by('-priority')[:5]
        popular_product = ProductPage.objects.order_by('old_price')[:10]
        category = CategoryPage.objects.all()[:4]
        banner = Banner.objects.order_by('-pk')[:4]
        banner_main=banner[0] if len(banner) >0 else None
        banner1 = banner[1] if len(banner) > 1 else None
        banner2 = banner[2] if len(banner) > 2 else None
        banner3 = banner[3] if len(banner) > 3 else None
        context = {
            'latest_products': latest_products,
            'featured_product': featured_product,
            'popular_product': popular_product,
            'category': category,
            'banner_main':banner_main,
            'banner1':banner1,
            'banner2':banner2,
            'banner3':banner3 }
        
        return render(request, 'home/index.html', context)
def home(request):
    products = ProductPage.objects.prefetch_related('variant').all()

    category_filter = request.GET.getlist('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_option = request.GET.get('sort')
    search_query = request.GET.get('search', '').strip()
    
    print(f"Filters - Category: {category_filter}, Price: {min_price}-{max_price}, Sort: {sort_option}, Search: {search_query}")

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    if category_filter:
        products = products.filter(category__name__in=category_filter)

    if min_price and max_price:
        try:
            min_price_decimal = Decimal(min_price)
            max_price_decimal = Decimal(max_price)
            products = products.filter(
                variant__price__gte=min_price_decimal,
                variant__price__lte=max_price_decimal
            ).distinct()
        except (ValueError, TypeError):
            pass  

    products_list = list(products)
    for product in products_list:
        highest_stock_variant = product.variant.order_by('-stock').first()
        product.largest_variant = highest_stock_variant
        if highest_stock_variant:
            product.display_price_value = highest_stock_variant.price
        else:
            product.display_price_value = product.price if product.price else 0

    if sort_option:
        if sort_option == 'price':
            products_list = sorted(products_list, key=lambda p: p.display_price_value or 0)
        elif sort_option == '-price':
            products_list = sorted(products_list, key=lambda p: p.display_price_value or 0, reverse=True)
        elif sort_option == 'name':
            products_list = sorted(products_list, key=lambda p: p.name.lower())
        elif sort_option == '-name':
            products_list = sorted(products_list, key=lambda p: p.name.lower(), reverse=True)
        elif sort_option == 'stock':
            products_list = sorted(products_list, key=lambda p: p.largest_variant.stock if p.largest_variant else 0, reverse=True)
        elif sort_option == '-created_at':
            products_list = sorted(products_list, key=lambda p: p.created_at, reverse=True)
        elif sort_option == 'created_at':
            products_list = sorted(products_list, key=lambda p: p.created_at)
    else:
        products_list = sorted(products_list, key=lambda p: p.largest_variant.stock if p.largest_variant else 0, reverse=True)
    paginator = Paginator(products_list, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    if request.user.is_authenticated:
        my_list = list(
            WishListItems.objects.filter(wish_list__user=request.user)
            .values_list("products_id", flat=True)
        )
    else:
        my_list = []

    context = {
        "products": products,
        "category": CategoryPage.objects.all(),
        "request": request,
        "my_list": my_list,
        "current_category": category_filter,
        "search_query": search_query,
    }

    return render(request, "home/home.html", context)
class Unlike(MyLoginRequiredMixin, View):
    def post(self, request, pid):
        WishListItems.objects.filter(products_id=pid, wish_list__user=request.user).delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))


class ProdectDetails(MyLoginRequiredMixin, DetailView):
    model = ProductPage
    template_name = 'home/product_details_page.html'
    context_object_name = 'product'
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        variants = product.variant.all()

        if self.request.user.is_authenticated:
            my_list = list(
                WishListItems.objects.filter(
                    wish_list__user=self.request.user
                ).values_list("products_id", flat=True)
            )
        else:
            my_list = []

        context["my_list"] = my_list

        variant_id = self.request.GET.get("variant")
        if variant_id:
            try:
                selected_variant = variants.get(id=variant_id)
                context["selected_variant"] = selected_variant
                context["variant_product"] = selected_variant
                context["is_variant_selected"] = True
                context["variant_original_price"] = selected_variant.get_original_price()
                context["variant_discounted_price"] = selected_variant.get_discounted_price()
            except ProductVariants.DoesNotExist:
                context["variant_product"] = product
                context["is_variant_selected"] = False
        else:
            if variants.exists():
                selected_variant = variants.first()
                context["selected_variant"] = selected_variant
                context["variant_product"] = selected_variant
                context["is_variant_selected"] = True
                context["variant_original_price"] = selected_variant.get_original_price()
                context["variant_discounted_price"] = selected_variant.get_discounted_price()
            else:
                context["variant_product"] = product
                context["selected_variant"] = None
                context["is_variant_selected"] = False

        context["variant_form"] = VarientSelectforms(
                queryset=variants,
                initial={'variant': selected_variant.id if selected_variant else None}
            )
        active_offer = product.get_active_offer()
        context["active_offer"] = active_offer
        context["has_offer"] = active_offer is not None
        context["discount_percentage"] = product.get_discount_percentage() if active_offer else 0
        
        context["reviews"] = Review.objects.filter(product_variant__product=product)
        context["review_form"] = ReviewForm()
        related_products = (
            ProductPage.objects.filter(category=product.category)
            .exclude(id=product.id)[:6]
        )
        context["related_products"] = related_products
        has_bought = False
        if self.request.user.is_authenticated:
            if selected_variant:
                has_bought = OrderItem.objects.filter(
                    order__user=self.request.user,
                    variant=selected_variant,
                    order__order_status=Orders.STATUS_DELIVERED
                ).exists()
        else:
            has_bought = OrderItem.objects.filter(
                order__user=self.request.user,
                variant__product=product,
                order__order_status=Orders.STATUS_DELIVERED
            ).exists()

        context["has_bought"] = has_bought

        return context


@login_required(login_url='/customer/')
def show_cart(request):
    cart_obj, created = Cart.objects.get_or_create(
        owner=request.user,
        defaults={'order_status': Cart.CART_STAGE}
    )

    cart_obj = Cart.objects.get(owner=request.user)
    context = {
        'cart': cart_obj,
        'total_items': cart_obj.total_items,
        'total_price': cart_obj.total_price,
    }

    return render(request, 'home/cart.html', context)


@login_required
def add_to_cart(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                quantity = int(request.POST.get('quantity', 1))
                product_id = request.POST.get('product_id')
                variant_id = request.POST.get('variant_id', None)

                if not product_id or quantity <= 0:
                    messages.error(request, "Invalid product or quantity.")
                    return redirect('home')

                try:
                    product = ProductPage.objects.get(id=product_id)
                except ProductPage.DoesNotExist:
                    messages.error(request, "Product not found.")
                    return redirect('home')

                variant = None
                display_name = product.name
                available_stock = product.stock

                if variant_id:
                    try:
                        variant = ProductVariants.objects.get(id=variant_id, product=product)
                        available_stock = variant.stock
                        display_name = f"{product.name} - {variant.variant.name}"
                    except ProductVariants.DoesNotExist:
                        variant = None

                if quantity > available_stock:
                    messages.error(request, f"Only {available_stock} items available in stock.",extra_tags="product-details")
                    return redirect('items_details', pk=product.id)

                cart_obj, cart_created = Cart.objects.get_or_create(
                    owner=request.user,
                    defaults={'order_status': Cart.CART_STAGE}
                )

                cart_item, item_created = CartItems.objects.get_or_create(
                    product=product,
                    owner=cart_obj,
                    variant=variant,
                    defaults={'quantity': quantity}
                )

                if not item_created:
                    new_quantity = cart_item.quantity + quantity
                    if new_quantity > available_stock:
                        messages.error(request, f"Cannot add more. Only {available_stock} items available.")
                        return redirect('cart')
                    cart_item.quantity = new_quantity
                    cart_item.save()
                    messages.success(request, f"Updated quantity for {display_name} in your cart.")
                else:
                    messages.success(request, f"Added {display_name} to your cart.")

                WishListItems.objects.filter(
                    products__id=product.id,
                    wish_list__user=request.user
                ).delete()

                return redirect('cart')

        except ValueError:
            messages.error(request, "Invalid quantity value.")
        except Exception as e:
            messages.error(request, "Error adding item to cart. Please try again.")
    
    return redirect('home')


@login_required
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(CartItems, id=item_id, owner__owner=request.user)
        product_name = cart_item.product.name if cart_item.product else "Item"
        cart_item.delete()
        messages.success(request, f"Removed {product_name} from your cart.")
    except Exception as e:
        messages.error(request, "Error removing item. Please try again.")

    return redirect('cart')


@login_required
@require_POST
def update_cart_item(request, item_id):
    try:
        cart_item = get_object_or_404(
            CartItems,
            id=item_id,
            owner__owner=request.user
        )
        
        try:
            new_quantity = int(request.POST.get('quantity'))
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid quantity'})

        if new_quantity < 1:
            return JsonResponse({
                'success': False,
                'error': 'Quantity must be at least 1.'
            })

        if cart_item.variant:
            max_stock = cart_item.variant.stock or 0
            item_price = cart_item.variant.get_discounted_price()
        else:
            max_stock = cart_item.product.stock or 0
            item_price = cart_item.product.get_display_price()
        
        if isinstance(item_price, int):
            item_price = Decimal(str(item_price))
        elif item_price is None:
            item_price = Decimal('0')
        else:
            item_price = Decimal(str(item_price))
        
        if new_quantity > max_stock:
            return JsonResponse({
                'success': False,
                'error': f'Only {max_stock} items in stock.'
            })

        cart_item.quantity = new_quantity
        cart_item.save(update_fields=['quantity'])

        cart = cart_item.owner
        cart_total = cart.total_price or Decimal('0')
        total_items = sum(item.quantity for item in cart.ordered_items.all())

        item_total = item_price * new_quantity

        return JsonResponse({
            'success': True,
            'item_total': float(item_total),
            'cart_total': float(cart_total),
            'total_items': total_items,
            'new_quantity': new_quantity,
        })
        
    except CartItems.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Cart item not found.'
        })
    except Exception as e:
        logger.exception("Error updating cart item")
        return JsonResponse({
            'success': False,
            'error': 'Error updating cart. Please try again.'
        })


def _get_item_price(cart_item):
    if cart_item.variant:
        price = cart_item.variant.get_discounted_price()
    else:
        price = cart_item.product.get_display_price()
    
    if price is None:
        price = Decimal('0')
    return Decimal(str(price))


def _validate_stock_availability(cart_items):

    items_needing_reduction = []
    
    for cart_item in cart_items:
        if not cart_item.product:
            return False, "Product unavailable in your cart", []
        
        if cart_item.variant:
            stock_source = cart_item.variant
            available_stock = stock_source.stock or 0
            product_name = f"{cart_item.product.name} - {stock_source.variant.name}"
        else:
            stock_source = cart_item.product
            available_stock = stock_source.stock or 0
            product_name = cart_item.product.name
        
        if available_stock < cart_item.quantity:
            return False, f"Insufficient stock for {product_name}. Available: {available_stock}, Requested: {cart_item.quantity}", []
        
        items_needing_reduction.append({
            'cart_item': cart_item,
            'stock_source': stock_source,
            'price': _get_item_price(cart_item),
            'product_name': product_name,
        })
    
    return True, "", items_needing_reduction




@transaction.atomic
def _finalize_order(
    user,
    cart,
    delivery_address,
    payment_method,
    razorpay_id=None,
    razorpay_payment_id=None,
    total_amount=None,
    coupon=None):
  
    if payment_method == 'razorpay':
        payment_method_const = Orders.ONLINE_PAYMENT
        payment_status = Orders.PAYMENT_PAID
    elif payment_method == 'wallet':
        payment_method_const = Orders.WALLET_PAYMENT
        payment_status = Orders.PAYMENT_PAID
    elif payment_method == 'cod':
        payment_method_const = Orders.CASH_ON_DELIVERY
        payment_status = Orders.PAYMENT_PENDING
    else:
        raise ValueError(f"Invalid payment method: {payment_method}")
    
    cart_items = list(cart.ordered_items.select_for_update().all())
    if not cart_items:
        raise ValueError("Cart is empty - no valid items found")
    
    is_valid, error_message, items_info = _validate_stock_availability(cart_items)
    if not is_valid:
        raise ValueError(error_message)
    
    if total_amount is None:
        total_amount = cart.total_price
    
    coupon_code = None
    coupon_obj = None
    
    if coupon:
        is_valid, error_message = coupon.is_valid(user=user)
        if not is_valid:
            raise ValueError(f"Coupon validation failed: {error_message}")
        
        if cart.subtotal < coupon.min_cart_value:
            raise ValueError(
                f"Cart value must be at least ₹{coupon.min_cart_value} "
                f"to use this coupon"
            )
        
        usage_count = CouponUsage.objects.filter(
            coupon=coupon,
            user=user
        ).count()
        
        if usage_count >= coupon.use_limit_per_user:
            raise ValueError(
                f"You have already used this coupon {coupon.use_limit_per_user} time(s)"
            )
        
        coupon_code = coupon.coupon_code
        coupon_obj = coupon
    
    # Create order
    order = Orders.objects.create(
        user=user,
        delivery_address=delivery_address,
        payment_method=payment_method_const,
        payment_status=payment_status,
        order_status=Orders.STATUS_CONFIRMED,
        total_amount=total_amount,
        razorpay_order_id=razorpay_id,
        razorpay_payment_id=razorpay_payment_id,
        coupon_code=coupon_obj,
        paid_at=timezone.now() if payment_status == Orders.PAYMENT_PAID else None,
    )
    
    logger.info(
        f"Order {order.pk} created with payment_method={payment_method}, "
        f"payment_status={payment_status}"
    )
    
    for item_info in items_info:
        cart_item = item_info['cart_item']
        stock_source = item_info['stock_source']
        price = item_info['price']
        stock_source.stock = F('stock') - cart_item.quantity
        stock_source.save(update_fields=["stock"])
        
        OrderItem.objects.create(
            order=order,
            product=cart_item.product,
            variant=cart_item.variant,
            quantity=cart_item.quantity,
            unit_price=price,
            order_status=Orders.STATUS_CONFIRMED,
        )
    
    if coupon_obj:
        try:
            CouponUsage.objects.create(
                coupon=coupon_obj,
                user=user,
                order=order
            )
            logger.info(
                f"Coupon '{coupon_code}' usage recorded for user {user.pk} "
                f"in order {order.pk}"
            )
        except Exception as e:
            logger.error(
                f"Failed to record coupon usage for order {order.pk}: {str(e)}"
            )
        
        try:
            cart.coupon_code = None
            cart.save(update_fields=['coupon_code'])
        except Exception as e:
            logger.error(
                f"Failed to remove coupon from cart for order {order.pk}: {str(e)}"
            )
    
    try:
        CartItems.objects.filter(owner=cart).delete()
        cart.delete()
    except Exception as e:
        logger.error(
            f"Failed to clear cart for order {order.pk}: {str(e)}"
        )
    
    logger.info(
        f"Order {order.pk} finalized successfully | User: {user.pk} | "
        f"Payment Method: {dict(Orders.PAYMENT_CHOICES).get(payment_method_const)} | "
        f"Payment Status: {dict(Orders.PAYMENT_STATUS_CHOICES).get(payment_status)} | "
        f"Amount: ₹{order.total_amount} | Coupon: {coupon_code or 'None'}"
    )
    
    return order




class CheckoutList(MyLoginRequiredMixin, View):

    def get(self, request):
        """Displays the checkout page with cart summary, addresses, and Razorpay initialization."""
        user = request.user
        
        cart = self._get_and_validate_cart(request, user)
        if redirect_response := self._check_for_empty_cart(request, cart):
            return redirect_response

        cart = self._validate_and_update_coupon(request, cart)
        context = self._build_base_context(user, cart, request)
        self._initialize_razorpay(context, cart.total_price)
        
        return render(request, 'home/checkout.html', context)


    @transaction.atomic
    def post(self, request):
        """Processes the selected address and payment method."""
        user = request.user
        address_id = request.POST.get('address', '').strip()
        payment_method = request.POST.get('payment_method', 'cod').strip()

        delivery_address, cart = self._get_address_and_cart(request, user, address_id)
        if isinstance(delivery_address, HttpResponseRedirect): return delivery_address

        applied_coupon = self._revalidate_coupon(request, cart)
        total_amount = cart.total_price or Decimal('0')

        if payment_method == 'razorpay':
            return self._handle_razorpay_payment(request, user, cart, delivery_address, total_amount, applied_coupon)
        elif payment_method == 'wallet':
            return self._handle_wallet_payment(request, user, cart, delivery_address, total_amount, applied_coupon)
        elif payment_method == 'cod':
            return self._handle_cod_payment(request, user, cart, delivery_address, total_amount, applied_coupon)
        else:
            messages.error(request, 'Invalid payment method.', extra_tags='order_failed')
            return redirect('order_failed')


    def _get_and_validate_cart(self, request, user):
        """Retrieves cart or returns None if it doesn't exist."""
        try:
            return Cart.objects.get(owner=user)
        except Cart.DoesNotExist:
            messages.error(request, 'No cart found.')
            return None

    def _check_for_empty_cart(self, request, cart):
        """Checks if the cart is empty and returns a redirect response if it is."""
        if not cart or not cart.ordered_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
        return None

    def _validate_and_update_coupon(self, request, cart):
        """Validates the existing coupon on the cart and updates the cart if invalid."""
        if cart.coupon_code:
            coupon = cart.coupon_code
            if not coupon.is_valid():
                messages.info(request, "Coupon removed as it is no longer valid.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
            elif cart.subtotal < coupon.min_cart_value:
                messages.info(request, f"Coupon removed. Cart must be at least ₹{coupon.min_cart_value}.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
        return cart

    def _build_base_context(self, user, cart, request):
        """Builds the common context dictionary."""
        wallet, created = Wallet.objects.get_or_create(user=user)
        addresses_queryset = OrderAddress.objects.filter(user=request.user).order_by('-id')
        
        paginator = Paginator(addresses_queryset, 3)
        page = request.GET.get('page', 1)
        addresses = paginator.get_page(page)

        return {
            'cart_items': cart.ordered_items.all(),
            'addresses': addresses,
            'subtotal': cart.subtotal,
            'coupon_discount': cart.coupon_discount,
            'total_price': cart.total_price or Decimal('0'),
            'cart': cart,
            'wallet': wallet,
            'applied_coupon': cart.coupon_code,
            'currency': 'INR',
        }

    def _initialize_razorpay(self, context, total_price):
        """Initializes a Razorpay order and updates the context."""
        currency = context.get('currency', 'INR')
        amount = int(total_price * 100)
        
        context['razorpay_order_id'] = ""
        context['razorpay_error'] = None

        try:
            razorpay_order = razorpay_client.order.create(dict(
                amount=amount,
                currency=currency,
                payment_capture='1'
            ))
            context['razorpay_order_id'] = razorpay_order['id']
            context['razorpay_merchant_key'] = settings.RAZORPAY_KEY_ID
            context['razorpay_amount'] = amount
            context['razorpay_available'] = True
        except Exception as e:
            context['razorpay_error'] = "Razorpay payment gateway unavailable. Try COD or Wallet."
            context['razorpay_available'] = False
            logger.error(f"Razorpay init failed: {str(e)}")



    def _get_address_and_cart(self, request, user, address_id):
        """Validates and retrieves the delivery address and cart."""
        if not address_id:
            messages.error(request, 'Please select your delivery address.')
            return redirect('checkout'), None

        try:
            delivery_address = OrderAddress.objects.get(id=address_id, user=user)
        except (OrderAddress.DoesNotExist, ValueError):
            messages.error(request, 'Invalid address selected.')
            return redirect('checkout'), None

        try:
            cart = Cart.objects.get(owner=user)
            if not cart.ordered_items.exists():
                messages.error(request, 'Your cart is empty.')
                return redirect('cart'), None
        except Cart.DoesNotExist as e:
            messages.error(request, 'No cart found.')
            logger.exception(str(e))
            return redirect('cart'), None

        return delivery_address, cart

    def _revalidate_coupon(self, request, cart):
        """Re-validates coupon just before order finalization and returns the coupon object."""
        applied_coupon = getattr(cart, 'coupon_code', None)

        if applied_coupon:
            if not applied_coupon.is_valid():
                messages.warning(request, "Coupon is not valid anymore. Removed automatically.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                return None
            
            if cart.subtotal < applied_coupon.min_cart_value:
                messages.warning(request, f"Cart must be at least ₹{applied_coupon.min_cart_value} to use this coupon.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                return None
        
        return cart.coupon_code


    def _handle_razorpay_payment(self, request, user, cart, delivery_address, total_amount, applied_coupon):
        """Handles the final verification and creation of an order paid via Razorpay."""
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
        razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
        razorpay_signature = request.POST.get('razorpay_signature', '').strip()

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            messages.error(request, "Payment failed or missing details.", extra_tags='order_failed')
            return redirect('order_failed')

        try:
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            razorpay_client.utility.verify_payment_signature(params_dict)

            order = _finalize_order(
                user=user, cart=cart, delivery_address=delivery_address, payment_method='razorpay',
                razorpay_id=razorpay_order_id, razorpay_payment_id=razorpay_payment_id,
                total_amount=total_amount, coupon=applied_coupon
            )
            
            messages.success(request, f"Payment successful! Order #{order.pk} confirmed.")
            return redirect(reverse('order_success', kwargs={'uid': order.pk}))

        except Exception as e:
            messages.error(request, "Payment verification failed. Please try again.", extra_tags='order_failed')
            logger.exception(f"Razorpay payment error for user {user.pk}: {e}")
            return redirect('order_failed')


    def _handle_wallet_payment(self, request, user, cart, delivery_address, total_amount, applied_coupon):
        """Handles the deduction from the wallet and creation of a wallet-paid order."""
        try:
            from wallet.models import Wallet, WalletTransaction # Re-importing locally as in original code
            wallet, created = Wallet.objects.get_or_create(user=user)

            if not wallet.has_sufficient_balance(total_amount):
                messages.error(request, f'Insufficient wallet balance. Your balance: ₹{wallet.balance}, Required: ₹{total_amount}')
                return redirect('order_failed')

            wallet.deduct_money(
                amount=total_amount,
                transaction_type=WalletTransaction.DEBIT_PURCHASE,
                description="Payment for order",
                reference_id=None 
            )

            order = _finalize_order(
                user=user, cart=cart, delivery_address=delivery_address, payment_method='wallet',
                total_amount=total_amount, coupon=applied_coupon
            )

            last_transaction = WalletTransaction.objects.filter(
                wallet=wallet, reference_id=None, transaction_type=WalletTransaction.DEBIT_PURCHASE
            ).order_by('-created_at').first()

            if last_transaction:
                last_transaction.reference_id = str(order.pk)
                last_transaction.save(update_fields=['reference_id'])

            messages.success(request, f'Order #{order.pk} confirmed! Paid via wallet.')
            return redirect(reverse('order_success', kwargs={'uid': order.pk}))

        except Exception as e:
            messages.error(request, "Error processing wallet payment.")
            logger.exception(f"Wallet payment error for user {user.pk}: {e}")
            return redirect('order_failed')


    def _handle_cod_payment(self, request, user, cart, delivery_address, total_amount, applied_coupon):
        """Handles the creation of a Cash on Delivery order."""
        try:
            order = _finalize_order(
                user=user, cart=cart, delivery_address=delivery_address, payment_method='cod',
                total_amount=total_amount, coupon=applied_coupon
            )
            
            messages.success(request, f'Order #{order.pk} confirmed!')
            return redirect(reverse('order_success', kwargs={'uid': order.pk}))
        except Exception as e:
            messages.error(request, "Error processing order.")
            logger.exception(f"Order processing error for user {user.pk}: {e}")
            return redirect('order_failed')    
        
def order_success(request, uid):
    try:
        order = Orders.objects.get(pk=uid, user=request.user)
        mark_referral_first_purchase(request.user)
        return render(request, 'home/order_success.html', {'order': order})
    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('home')


class unlike(MyLoginRequiredMixin, View):
    def post(self, request, pid):
        WishListItems.objects.filter(products_id=pid, wish_list__user=request.user).delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))


def apply_coupon_to_cart(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code", "").strip()
        cart = request.user.cart  
        
        try:
            coupon = Coupons.objects.get(coupon_code=code)
        except Coupons.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect("checkout")
        
        if not coupon.active:
            messages.error(request, "Coupon is inactive.")
            return redirect("checkout")
        if coupon.expire_at < timezone.now().date():
            messages.error(request, "Coupon has expired.")
            return redirect("checkout")
        if coupon.use_limit <= 0:
            messages.error(request, "Coupon usage limit reached.")
            return redirect("checkout")
        if cart.total_price < coupon.min_cart_value:
            messages.error(request, f"Minimum cart value for this coupon is ₹{coupon.min_cart_value}.")
            return redirect("checkout")
        
        cart.coupon = coupon
        cart.save()
        
        messages.success(request, f"Coupon '{coupon.coupon_code}' applied successfully!")
        return redirect("checkout")
    
@login_required
def add_review(request, variant_id):
    variant = get_object_or_404(ProductVariants, id=variant_id)
    
    has_bought = OrderItem.objects.filter(
        order__user=request.user,
        variant=variant,
        order__order_status=Orders.STATUS_DELIVERED 
    ).exists()
    
    if not has_bought:
        messages.error(request, "You can only review products you have purchased and received.",extra_tags='product-details')
        
        return redirect('items_details', pk=variant.product.pk)
    
    existing_review = Review.objects.filter(
        user=request.user,
        product_variant=variant
    ).first()
    
    if request.method == "POST":
        try:
            rating = request.POST.get('rating')
            comment = request.POST.get('comment', '').strip()
            
            if not rating or not comment:
                messages.error(request, "Please provide both rating and comment.")
                return render(request, 'reviews/add_review.html', {
                    'variant': variant,
                    'existing_review': existing_review
                })
            
            rating = int(rating)
            if rating < 1 or rating > 5:
                messages.error(request, "Rating must be between 1 and 5.")
                return render(request, 'reviews/add_review.html', {
                    'variant': variant,
                    'existing_review': existing_review
                })
            
            Review.objects.update_or_create(
                user=request.user,
                product_variant=variant,
                defaults={'rating': rating, 'comment': comment}
            )
            
            messages.success(request, "Your review has been submitted successfully!",extra_tags="'product-details'")
            return redirect('items_details', pk=variant.product.pk)
            
        except ValueError:
            messages.error(request, "Invalid rating value.",extra_tags="add_review")
        except Exception as e:
            messages.error(request, "Please buy the product and try again.")
    
    context = {
        'variant': variant,
        'product': variant.product,
        'existing_review': existing_review
    }
    return render(request, 'product/add_review.html', context)

def about(request):
    return render(request,'about.html')

def contact_us(request):
    return render(request,'contact_us.html')


class OrderFailed(View):
    def get(self,request):
        return render(request,'home/order_failed.html')
