from django.shortcuts import render, redirect,get_object_or_404,HttpResponseRedirect
from products.models import ProductPage
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.views.generic import DetailView, View
from products.models import ProductPage
from category.models import CategoryPage
from orders.models import Cart, CartItems,OrderAddress,Orders,OrderItem
from django.db import transaction
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from customer.models import UserAddress,Register
from django.db.models import F, Sum,Count,Max
from django.contrib.auth.mixins import LoginRequiredMixin
from wish_list.models import WishListItems
User = get_user_model()
from django.urls import reverse

# Create your views here.


class Index(View):
    def get(self, request):
        latest_products = ProductPage.objects.order_by('-pk')[:5]  # pylint: disable=no-member
        featured_product = ProductPage.objects.order_by('priority')[:5]  # pylint: disable=no-member
        popular_product = ProductPage.objects.order_by('price')[:10]  # pylint: disable=no-member
        category = CategoryPage.objects.all()[:4]  # pylint: disable=no-member


        context = {
            'latest_products': latest_products,
            'featured_product': featured_product,
            'popular_product': popular_product,
            'category': category,
        }
        
        
        return render(request, 'home/index.html', context)


def home(request):
    
    products = ProductPage.objects.all()  # pylint: disable=no-member
    
    
    if request.user.is_authenticated:
        my_list = list(
                         WishListItems.objects.filter(wish_list__user=request.user).values_list("products_id", flat=True))

    else:
        my_list = WishListItems.objects.none()
        
        
        
    product_sort=request.GET.get('sort')
    allowed_sorts = ["price", "-price", "name", "-name", "created_at", "-created_at"]

    if product_sort in allowed_sorts:
        products = products.order_by(product_sort)

        
        
        
        
    total=ProductPage.objects.aggregate(total=Max("price"))['total'] or 0   # pylint: disable=no-member
    search=request.GET.get("search")
    
    if search:
        products=ProductPage.objects.filter(name__icontains=search)     # pylint: disable=no-member
    
    category_filter = request.GET.getlist("category")
    minimum_price_prm=request.GET.get('min_price')
    maximum_price_prm=request.GET.get('max_price')      
    minimum_price=int(minimum_price_prm) if minimum_price_prm not in [None , ''] else 0 
    maximum_price=int(maximum_price_prm) if maximum_price_prm not in [None , ''] else total
    if minimum_price or maximum_price:
        products=products.filter(price__gte=minimum_price , price__lte=maximum_price)
    if category_filter:
        products = products.filter(category__name__in=category_filter)
    
    page = request.GET.get('page', 1)
    product_paginator = Paginator(products, 10)
    products = product_paginator.get_page(page)
    
    categories = CategoryPage.objects.all()  # pylint: disable=no-member

    context = {
        'products': products,
        'category': categories,  
        'current_category': category_filter,
        'my_list': my_list, 
        
    }
    
    return render(request, 'home/home.html', context)

class unlike(LoginRequiredMixin ,View):
    def post(self , request , pid):
        WishListItems.objects.filter(products_id=pid, wish_list__user=request.user).delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER') or reverse('wish_list'))
  


class ProdectDetails(DetailView):
    model = ProductPage
    fields = ['image1', 'image2', 'image3', 'image4', 'image5','name', 'description', 'price', 'old_price', 'category']
    template_name = 'home/product_details_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.get_object()

        related_products = ProductPage.objects.filter(  # pylint: disable=no-member
            category=product.category
        ).exclude(id=product.id)[:4]

        context["related_products"] = related_products
        return context


@login_required
def show_cart(request):
    try:
        cart_obj, created = Cart.objects.get_or_create(    #pylint: disable=no-member
            owner=request.user,
            defaults={'order_status': Cart.CART_STAGE}
        )

        cart_items = cart_obj.ordered_items.all()
        context = {
            'cart': cart_obj,
            'cart_items': cart_items,
            'total_items': cart_obj.total_items,
            'total_price': cart_obj.total_price,
        }
        return render(request, 'home/cart.html', context)
    except Exception as e:
        messages.error(request, f"Error Loading cart: {str(e)}")
        return redirect('home')


@login_required
def add_to_cart(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                quantity = int(request.POST.get('quantity', 1))
                product_id = request.POST.get('product_id')

                if not product_id or quantity <= 0:
                    messages.error(request, "Invalid product or quantity.")
                    return redirect('home')
                
                
                

                product = get_object_or_404(ProductPage, id=product_id)

                cart_obj, created = Cart.objects.get_or_create(      #pylint: disable=no-member
                    owner=request.user,
                    defaults={'order_status': Cart.CART_STAGE}
                )

                cart_item, item_created = CartItems.objects.get_or_create(              #pylint: disable=no-member
                    product=product,
                    owner=cart_obj,
                    defaults={'quantity': quantity}
                )

                if not item_created:
                    cart_item.quantity += quantity
                    cart_item.save()
                    messages.success(
                        request, f"Updated quantity for {product.name} in your cart.")
                else:
                    messages.success(
                        request, f"Added {product.name} to your cart.")
                    
                    
                items=WishListItems.objects.filter(products__id=product.id)             #pylint: disable=no-member
                if items:
                    items.delete()
                    

                return redirect('cart')

        except ValueError:
            messages.error(request, "Invalid quantity value.")
        except Exception as e:
            messages.error(request, f"Error adding item to cart: {str(e)}")

    return redirect('home')


@login_required
def remove_from_cart(request, item_id):
    try:
        cart_item = get_object_or_404(                               #pylint: disable=no-member
        
            CartItems, id=item_id, owner__owner=request.user)
        product_name = cart_item.product.name if cart_item.product else "Item"
        cart_item.delete()
        messages.success(request, f"Removed {product_name} from your cart.")
    except Exception as e:
        messages.error(request, f"Error removing item: {str(e)}")

    return redirect('cart')


@login_required
def update_cart_item(request, item_id):
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            cart_item = get_object_or_404(                                       #pylint: disable=no-member
        
                CartItems, id=item_id, owner__owner=request.user)

            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, "Cart updated successfully.")
            else:
                cart_item.delete()
                messages.success(request, "Item removed from cart.")

        except ValueError:
            messages.error(request, "Invalid quantity value.")
        except Exception as e:
            messages.error(request, f"Error updating cart: {str(e)}")

    return redirect('cart')


        
class CheckoutList(View):
    def get(self ,request):
        user=request.user
        cart=Cart.objects.get(owner=user) #pylint: disable=no-member
        
        cart_items=cart.ordered_items.all()
        total_items=CartItems.objects.filter(owner=cart).aggregate(total_price=Sum(F('quantity') * F('product__price')))['total_price'] or 0   #pylint: disable=no-member
        
        addresses=OrderAddress.objects.filter(user=request.user)     #pylint: disable=no-member
        
        context={
            'cart_items':cart_items,
            'addresses':addresses,
            'total_items':total_items
        }
        
        
        return render(request, 'home/checkout.html',context)
    
    def post(self, request):
        user = request.user
        
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method', 'cod')
            
        if not address:
            messages.error(request, 'Please select your delivery address.')
            return redirect('checkout')
            
        try:
            delivery_address = OrderAddress.objects.get(id=address, user=user)    #pylint: disable=no-member
        except OrderAddress.DoesNotExist:        #pylint: disable=no-member
            messages.error(request, 'Invalid address selected.')
            return redirect('checkout')
        
        try:
            cart = Cart.objects.get(owner=user)      #pylint: disable=no-member
            if not cart.ordered_items.exists():
                messages.error(request, 'Your cart is empty.')
                return redirect('cart')
        except Cart.DoesNotExist:          #pylint: disable=no-member
            messages.error(request, 'No cart found.')
            return redirect('cart')
        
        register_user = user 
        
        try:
            with transaction.atomic():
                order = Orders.objects.create(     #pylint: disable=no-member
                    user=register_user,
                    delivery_address=delivery_address,
                    payment_method=Orders.CASH_ON_DELIVERY if payment_method == 'cod' else Orders.ONLINE_PAYMENT,
                    payment_status=Orders.PENDING,
                    order_status=1,
                    total_amount=cart.total_price
                    )
                    
                items_created = 0
                for cart_item in cart.ordered_items.all():
                    if cart_item.product:
                        OrderItem.objects.create(    #pylint: disable=no-member       
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            unit_price=cart_item.product.price,
                        )
                        items_created += 1
                    else:
                        messages.warning(request, f"Product no longer available: {cart_item}")                
                if items_created == 0:
                    messages.error(request, "No valid items found in cart.")
                    
                    return redirect('checkout')
                                
                    
                cart.ordered_items.all().delete()
                cart.order_status = Cart.ORDER_CONFIRMED
                cart.save()

    
                messages.success(request, f'Your order #{order.id} was confirmed.')
                return redirect('order_success')
            
        except Exception as e:
            messages.error(request, f"Error processing order: {str(e)}")
            return redirect('checkout')
        
def order_success(request):
    return render(request,'home/order_success.html')