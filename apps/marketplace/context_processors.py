from .models import Cart, Wishlist, Category


def marketplace_context(request):
    cart_count = 0
    wishlist_count = 0
    categories = []

    try:
        categories = Category.objects.all()[:12]
    except Exception:
        pass

    try:
        if request.user.is_authenticated:
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart_count = cart.items.count()
        else:
            session_key = request.session.session_key
            if session_key:
                cart = Cart.objects.filter(session_key=session_key).first()
                if cart:
                    cart_count = cart.items.count()
    except Exception:
        pass

    return {
        'cart_count': cart_count,
        'wishlist_count': wishlist_count,
        'nav_categories': categories,
    }
