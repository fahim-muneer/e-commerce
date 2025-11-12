from orders.models import Cart

def cart_context(request):
    """ cart available in all templates"""
    cart_data = {
        'cart_items': None,
        'cart_count': 0,
    }
    
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(owner=request.user)
            cart_data['cart_items'] = cart
            cart_data['cart_count'] = cart.total_items
        except Cart.DoesNotExist:
            pass
    
    return cart_data