from django.shortcuts import redirect, render, HttpResponseRedirect, get_object_or_404
from products.models import ProductPage
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.views.generic import DetailView, View
from category.models import CategoryPage
from orders.models import Cart, CartItems, OrderAddress, Orders, OrderItem
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from customer.models import UserAddress, Register
from django.db.models import F, Sum, Count, Max
from django.contrib.auth.mixins import LoginRequiredMixin
from wish_list.models import WishListItems
User = get_user_model()
from django.urls import reverse
from varients.models import Varient
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
from coupon.models import Coupons
logger = logging.getLogger(__name__)
from datetime import date
from wallet.models import Wallet
from django.db.models import Min, Max, Q
from products.forms import ReviewForm

razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)


class Index(View):
    def get(self, request):
        latest_products = ProductPage.objects.order_by('-pk')[:5]
        featured_product = ProductPage.objects.order_by('-priority')[:5]
        popular_product = ProductPage.objects.order_by('old_price')[:10]
        category = CategoryPage.objects.all()[:4]

        context = {
            'latest_products': latest_products,
            'featured_product': featured_product,
            'popular_product': popular_product,
            'category': category,
        }
        
        return render(request, 'home/index.html', context)
def home(request):
    products = ProductPage.objects.prefetch_related('variant').all()

    # Get ALL filter parameters
    category_filter = request.GET.getlist('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    sort_option = request.GET.get('sort')
    search_query = request.GET.get('search', '').strip()
    
    print(f"Filters - Category: {category_filter}, Price: {min_price}-{max_price}, Sort: {sort_option}, Search: {search_query}")

    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Apply category filter
    if category_filter:
        products = products.filter(category__name__in=category_filter)

    # Apply price filter on variants
    if min_price and max_price:
        try:
            min_price_decimal = Decimal(min_price)
            max_price_decimal = Decimal(max_price)
            products = products.filter(
                variant__price__gte=min_price_decimal,
                variant__price__lte=max_price_decimal
            ).distinct()
        except (ValueError, TypeError):
            pass  # Invalid price values, ignore filter

    # Attach largest_variant and display_price to each product
    products_list = list(products)
    for product in products_list:
        highest_stock_variant = product.variant.order_by('-stock').first()
        product.largest_variant = highest_stock_variant
        if highest_stock_variant:
            product.display_price_value = highest_stock_variant.price
        else:
            product.display_price_value = product.price if product.price else 0

    # Apply sorting
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
        # Default: Sort by stock (highest first)
        products_list = sorted(products_list, key=lambda p: p.largest_variant.stock if p.largest_variant else 0, reverse=True)

    # Pagination
    paginator = Paginator(products_list, 10)
    page = request.GET.get('page')
    products = paginator.get_page(page)

    # Get wishlist
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
                context["variant_product"] = selected_variant
                context["is_variant_selected"] = True
                context["variant_original_price"] = selected_variant.get_original_price()
                context["variant_discounted_price"] = selected_variant.get_discounted_price()
            else:
                context["variant_product"] = product
                context["is_variant_selected"] = False

        context["variant_form"] = VarientSelectforms(queryset=variants)
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
                    messages.error(request, f"Only {available_stock} items available in stock.")
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
            logger.exception("Error adding item to cart")
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
        logger.exception("Error removing item from cart")
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
    coupon=None
):
    print("...............finalized funcion was called...........")
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
    if coupon:
        if coupon.expire_at < timezone.now().date():
            raise ValueError("Coupon has expired.")
        if coupon.use_limit <= 0:
            raise ValueError("Coupon usage limit reached.")
        coupon_code = coupon.coupon_code
        coupon_code=Coupons.objects.get(coupon_code=coupon_code)
        # total_amount -= coupon.discount_value
        # total_amount = max(total_amount, 0)
        print("coupon is applied in finalize function for order")

    order = Orders.objects.create(
        user=user,
        delivery_address=delivery_address,
        payment_method=payment_method_const,
        payment_status=payment_status,
        order_status=Orders.STATUS_CONFIRMED,
        total_amount=total_amount,
        razorpay_order_id=razorpay_id,
        razorpay_payment_id=razorpay_payment_id,
        coupon_code=coupon_code,  
        paid_at=timezone.now() if payment_status == Orders.PAYMENT_PAID else None,
    )
    print("the order created in the finalized function")
    logger.info(f"Order {order.pk} created with payment_method={payment_method}, payment_status={payment_status}")

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
        print("order item created in finalized function")

    if coupon:
        coupon.use_limit -= 1
        coupon.save(update_fields=['use_limit'])
        cart.coupon_code = None
        cart.save(update_fields=['coupon_code'])       
        print("the coupon updated and decrease its limit in finalized function ")

    CartItems.objects.filter(owner=cart).delete()
    cart.delete()
    print("the cart deleted from the finalized function ")

    logger.info(
        f"Order {order.pk} created successfully | User: {user.pk} | "
        f"Payment Method: {dict(Orders.PAYMENT_CHOICES).get(payment_method_const)} | "
        f"Payment Status: {dict(Orders.PAYMENT_STATUS_CHOICES).get(payment_status)} | "
        f"Amount: ₹{order.total_amount} | Coupon: {coupon_code or 'None'}"
    )
    print('returning the finaized function to CHECKOUT PAGE')
    return order

def create_order_from_cart(cart):
    order = Orders.objects.create(
        user=cart.owner,
        total_amount=cart.total_price,
        coupon_code=cart.coupon if hasattr(cart, 'coupon') else None,
        delivery_address=cart.owner.default_address,  
        payment_method=Orders.CASH_ON_DELIVERY
    )

    for item in cart.ordered_items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.unit_price 
        )



    return order

class CheckoutList(MyLoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        try:
            cart = Cart.objects.get(owner=user)
        except Cart.DoesNotExist:
            messages.error(request, 'No cart found.')
            return redirect('cart')

        if not cart.ordered_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')

        if cart.coupon_code:
            coupon = cart.coupon_code
            if not coupon.is_valid():
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                print("Removed invalid coupon (expired/inactive/used up)")
            elif cart.subtotal < coupon.min_cart_value:
                messages.info(request, f"Coupon removed. Cart must be at least ₹{coupon.min_cart_value}.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                print("Cart subtotal not eligible for coupon")

        cart_items = cart.ordered_items.all()
        subtotal = cart.subtotal
        print(f"Subtotal before coupon applied: {subtotal}")
        coupon_discount = cart.coupon_discount
        print(f"Coupon discount amount: {coupon_discount}")
        total_price = cart.total_price or Decimal('0')
        print(f"Total price of the cart: {total_price}")
        print("============================================================================================")
        print(f" Subtotal: {subtotal}, Discount: {coupon_discount}, Total: {total_price}")

        wallet, created = Wallet.objects.get_or_create(user=user)
        applied_coupon = cart.coupon_code 

        addresses_queryset = OrderAddress.objects.filter(user=request.user).order_by('-id')
        page = request.GET.get('page', 1)
        paginator = Paginator(addresses_queryset, 3)
        addresses = paginator.get_page(page)

        currency = 'INR'
        amount = int(total_price * 100)
        razorpay_order_id = ""
        razorpay_error = None

        try:
            razorpay_order = razorpay_client.order.create(dict(
                amount=amount,
                currency=currency,
                payment_capture='1'
            ))
            razorpay_order_id = razorpay_order['id']
        except Exception as e:
            razorpay_error = "Razorpay payment gateway unavailable. Try COD or Wallet."
            logger.error(f"Razorpay init failed: {str(e)}")

        context = {
            'cart_items': cart_items,
            'addresses': addresses,
            'subtotal': subtotal,
            'coupon_discount': coupon_discount,
            'total_price': total_price,
            'cart': cart,
            'wallet': wallet,
            'applied_coupon': applied_coupon,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_merchant_key': settings.RAZORPAY_KEY_ID if razorpay_order_id else None,
            'razorpay_amount': amount,
            'currency': currency,
            'razorpay_error': razorpay_error,
            'razorpay_available': bool(razorpay_order_id),
        }

        return render(request, 'home/checkout.html', context)

    @transaction.atomic
    def post(self, request):
        
        print("checkout processing started")
        user = request.user
        print(f"user{user}")
        
        address_id = request.POST.get('address', '').strip()
        print(f"address{address_id}")
        payment_method = request.POST.get('payment_method', 'cod').strip()
        print(f"payment mrthod{payment_method}")

        if not address_id:
            messages.error(request, 'Please select your delivery address.')
            print("no address found, and redirected")
            return redirect('checkout')

        try:
            delivery_address = OrderAddress.objects.get(id=address_id, user=user)
            print("delivery address got")
        except (OrderAddress.DoesNotExist, ValueError):
            messages.error(request, 'Invalid address selected.')
            print("invalid address so redirected and redirected")
            return redirect('checkout')

        try:
            cart = Cart.objects.get(owner=user)
            if not cart.ordered_items.exists():
                messages.error(request, 'Your cart is empty.')
                print("cart is empty so redirected")
                return redirect('cart')
        except Cart.DoesNotExist as e:
            messages.error(request, 'No cart found.')
            logger.exception(str(e))
            print("no cart found  so redirected")
            return redirect('cart')

        total_amount = cart.total_price or Decimal('0')
        print(f"total amount is {total_amount}")

        applied_coupon = getattr(cart, 'coupon_code', None)
        print(f"applied coupon is {applied_coupon}")

        if applied_coupon:
            if not applied_coupon.is_valid():
                messages.warning(request, "Coupon is not valid anymore. Removed automatically.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                applied_coupon = None
            elif cart.subtotal < applied_coupon.min_cart_value:
                messages.warning(request, f"Cart must be at least ₹{applied_coupon.min_cart_value} to use this coupon.")
                cart.coupon_code = None
                cart.save(update_fields=['coupon_code'])
                applied_coupon = None

        if payment_method == 'razorpay':
            razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
            razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
            razorpay_signature = request.POST.get('razorpay_signature', '').strip()

            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                messages.error(request, "Payment failed or missing details.")
                print("pyment failed and redirected")
                return redirect('checkout')

            try:
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }
                razorpay_client.utility.verify_payment_signature(params_dict)

                order = _finalize_order(
                    user=user,
                    cart=cart,
                    delivery_address=delivery_address,
                    payment_method='razorpay',
                    razorpay_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    total_amount=total_amount,
                    coupon=applied_coupon
                )

             
                messages.success(request, f"Payment successful! Order #{order.pk} confirmed.")
                print("seccess redirected")
                return redirect(reverse('order_success', kwargs={'uid': order.pk}))

            except Exception as e:
                messages.error(request, "Payment verification failed. Please try again.")
                logger.exception(f"Razorpay payment error for user {user.pk}: {e}")
                print(f"the error is {str(e)}")
                return redirect('checkout')

        elif payment_method == 'wallet':
            try:
                from wallet.models import Wallet, WalletTransaction
                wallet, created = Wallet.objects.get_or_create(user=user)

                if not wallet.has_sufficient_balance(total_amount):
                    messages.error(request, f'Insufficient wallet balance. Your balance: ₹{wallet.balance}, Required: ₹{total_amount}')
                    return redirect('checkout')

                wallet.deduct_money(
                    amount=total_amount,
                    transaction_type=WalletTransaction.DEBIT_PURCHASE,
                    description="Payment for order",
                    reference_id=None
                )

                order = _finalize_order(
                    user=user,
                    cart=cart,
                    delivery_address=delivery_address,
                    payment_method='wallet',
                    total_amount=total_amount,
                    coupon=applied_coupon
                )

              

                last_transaction = WalletTransaction.objects.filter(
                    wallet=wallet,
                    reference_id=None,
                    transaction_type=WalletTransaction.DEBIT_PURCHASE
                ).order_by('-created_at').first()

                if last_transaction:
                    last_transaction.reference_id = str(order.pk)
                    last_transaction.save(update_fields=['reference_id'])

                messages.success(request, f'Order #{order.pk} confirmed! Paid via wallet.')
                return redirect(reverse('order_success', kwargs={'uid': order.pk}))

            except ValueError as e:
                messages.error(request, str(e))
                return redirect('checkout')
            except Exception as e:
                messages.error(request, "Error processing wallet payment.")
                logger.exception(f"Wallet payment error for user {user.pk}: {e}")
                return redirect('checkout')

        elif payment_method == 'cod':
            try:
                order = _finalize_order(
                    user=user,
                    cart=cart,
                    delivery_address=delivery_address,
                    payment_method='cod',
                    total_amount=total_amount,
                    coupon=applied_coupon
                )

               
                messages.success(request, f'Order #{order.pk} confirmed!')
                return redirect(reverse('order_success', kwargs={'uid': order.pk}))
            except Exception as e:
                messages.error(request, "Error processing order.")
                logger.exception(f"Order processing error for user {user.pk}: {e}")
                return redirect('checkout')

        else:
            messages.error(request, 'Invalid payment method.')
            return redirect('checkout')

        
        
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
    print("Getting into the add review function")
    variant = get_object_or_404(ProductVariants, id=variant_id)
    print(f"Variant is = {variant}")
    
    has_bought = OrderItem.objects.filter(
        order__user=request.user,
        variant=variant,
        order__order_status=Orders.STATUS_DELIVERED 
    ).exists()
    
    if not has_bought:
        messages.error(request, "You can only review products you have purchased and received.",extra_tags='product-details')
        print("User hasn't purchased this product")
        
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
            print("Review submitted successfully!")
            return redirect('items_details', pk=variant.product.pk)
            
        except ValueError:
            messages.error(request, "Invalid rating value.",extra_tags="add_review")
            print("Invalid rating value")
        except Exception as e:
            messages.error(request, "Please buy the product and try again.")
            print(f"The error is: {str(e)}")
    
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