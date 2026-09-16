from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F, Count, Sum
from django.utils import timezone
from django.contrib import messages
from .models import Category, Product, Review, Wishlist, Cart, CartItem, ProductView
from apps.accounts.models import SellerProfile
from apps.orders.models import Order, OrderItem
from apps.notifications.models import Notification


def home_view(request):
    featured_categories = Category.objects.filter(is_featured=True).annotate(
        approved_count=Count('products', filter=Q(products__status='approved'))
    )[:8]
    if not featured_categories.exists():
        featured_categories = Category.objects.all().annotate(
            approved_count=Count('products', filter=Q(products__status='approved'))
        )[:8]

    approved_products = Product.objects.filter(status='approved').select_related('seller', 'category')

    trending_products = approved_products.order_by('-views_count', '-sales_count')[:4]
    best_sellers = approved_products.filter(sales_count__gt=0).order_by('-sales_count')[:4]
    if not best_sellers.exists():
        best_sellers = approved_products.order_by('-rating')[:4]
    new_products = approved_products.order_by('-created_at')[:4]
    top_creators = SellerProfile.objects.select_related('user').annotate(
        approved_products_count=Count('products', filter=Q(products__status='approved'))
    ).order_by('-total_sales', '-rating')[:4]

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    total_products_count = approved_products.count()
    total_sellers_count = SellerProfile.objects.count()
    total_paid_orders = Order.objects.filter(status='paid')
    total_sales_count = total_paid_orders.count()

    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_orders = total_paid_orders.filter(created_at__gte=today_start)
    today_count = today_orders.count()
    today_volume = today_orders.aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')

    all_time_volume = total_paid_orders.aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')

    if today_count > 0:
        hero_summary = {
            'label': 'Bugungi jami savdolar',
            'value': f"{today_volume:,.0f} UZS",
            'badge': f"{today_count} ta muvaffaqiyatli bitim",
            'sub_badge': '+Bugun faol',
        }
    elif all_time_volume > 0:
        hero_summary = {
            'label': 'Jami muvaffaqiyatli savdolar',
            'value': f"{all_time_volume:,.0f} UZS",
            'badge': f"{total_sales_count} ta muvaffaqiyatli bitim",
            'sub_badge': 'Platforma faol',
        }
    else:
        hero_summary = {
            'label': 'Mavjud raqamli mahsulotlar',
            'value': f"{total_products_count} ta tayyor loyiha",
            'badge': f"{total_sellers_count} ta faol muallif",
            'sub_badge': 'Yangi katalog',
        }

    recent_order_items = OrderItem.objects.filter(order__status='paid').select_related(
        'order__user', 'product__category', 'seller'
    ).order_by('-order__created_at')[:3]

    hero_activity = []
    icon_colors = ['hero-icon-blue', 'hero-icon-purple', 'hero-icon-amber']

    if recent_order_items.exists():
        for idx, item in enumerate(recent_order_items):
            buyer_user = item.order.user
            first_n = buyer_user.first_name or buyer_user.username
            buyer_display = f"{first_n[:7]}..." if len(first_n) > 8 else first_n
            cat_icon = item.product.category.icon if item.product and item.product.category else '🚀'
            color_cls = icon_colors[idx % len(icon_colors)]

            hero_activity.append({
                'icon': cat_icon,
                'color_class': color_cls,
                'title': item.product_title,
                'price': f"+{item.price:,.0f} UZS",
                'meta': f"{buyer_display} • xarid qilindi",
                'created_at': item.order.created_at,
                'status': 'To‘landi ✅',
                'url': f"/product/{item.product.slug}/" if item.product else '#',
            })
    else:
        top_samples = approved_products.order_by('-rating', '-created_at')[:3]
        for idx, prod in enumerate(top_samples):
            color_cls = icon_colors[idx % len(icon_colors)]
            price_str = "Tekin" if prod.is_free else f"{prod.effective_price:,.0f} UZS"
            hero_activity.append({
                'icon': prod.category.icon if prod.category else '💻',
                'color_class': color_cls,
                'title': prod.title,
                'price': price_str,
                'meta': f"{prod.seller.store_name} • yangi mahsulot",
                'created_at': prod.created_at,
                'status': 'Katalogda ✅',
                'url': f"/product/{prod.slug}/",
            })

    stats = {
        'products_count': total_products_count,
        'sellers_count': total_sellers_count,
        'sales_count': total_sales_count,
    }

    return render(request, 'home.html', {
        'featured_categories': featured_categories,
        'trending_products': trending_products,
        'best_sellers': best_sellers,
        'new_products': new_products,
        'top_creators': top_creators,
        'stats': stats,
        'hero_summary': hero_summary,
        'hero_activity': hero_activity,
        'user_wishlist_ids': user_wishlist_ids,
    })


def marketplace_view(request):
    products = Product.objects.filter(status='approved').select_related('seller', 'category')
    all_categories = Category.objects.all()

    category_slug = request.GET.get('category', '').strip()
    price_type = request.GET.get('price_type', 'all')
    min_rating = request.GET.get('min_rating', '0')
    sort = request.GET.get('sort', 'recommended')
    search_query = request.GET.get('q', '').strip()

    if search_query:
        products = products.filter(
            Q(title__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )

    if category_slug:
        products = products.filter(category__slug=category_slug)

    if price_type == 'free':
        products = products.filter(is_free=True)
    elif price_type == 'paid':
        products = products.filter(is_free=False, price__gt=0)

    try:
        min_rating_val = float(min_rating)
        if min_rating_val > 0:
            products = products.filter(rating__gte=min_rating_val)
    except ValueError:
        pass

    if sort == 'popular':
        products = products.order_by('-views_count', '-sales_count')
    elif sort == 'sales':
        products = products.order_by('-sales_count')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    elif sort == 'rating':
        products = products.order_by('-rating', '-reviews_count')
    elif sort == 'price_low':
        products = products.order_by('price')
    elif sort == 'price_high':
        products = products.order_by('-price')
    else:
        products = products.order_by('-sales_count', '-views_count', '-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    query_dict = request.GET.copy()
    if 'page' in query_dict:
        query_dict.pop('page')
    current_query_with_sort = query_dict.urlencode()

    if 'sort' in query_dict:
        query_dict.pop('sort')
    current_query_without_sort = query_dict.urlencode()

    return render(request, 'marketplace/marketplace.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'all_categories': all_categories,
        'selected_category': category_slug,
        'selected_price_type': price_type,
        'selected_min_rating': min_rating,
        'current_sort': sort,
        'search_query': search_query,
        'total_count': paginator.count,
        'user_wishlist_ids': user_wishlist_ids,
        'current_query_with_sort': current_query_with_sort,
        'current_query_without_sort': current_query_without_sort,
    })


def product_detail_view(request, slug):
    product = get_object_or_404(Product.objects.select_related('seller', 'category'), slug=slug)

    if product.status != 'approved':
        if not (request.user.is_authenticated and (request.user.is_staff or (hasattr(request.user, 'seller_profile') and product.seller == request.user.seller_profile))):
            from django.http import Http404
            raise Http404("Mahsulot mavjud emas.")

    Product.objects.filter(pk=product.pk).update(views_count=F('views_count') + 1)
    ProductView.objects.create(
        product=product,
        user=request.user if request.user.is_authenticated else None,
        ip_address=request.META.get('REMOTE_ADDR')
    )

    related_products = Product.objects.filter(
        category=product.category, status='approved'
    ).exclude(id=product.id).select_related('seller', 'category')[:4]

    is_purchased = False
    purchased_item_id = None
    is_wishlisted = False
    user_has_reviewed = False

    if request.user.is_authenticated:
        order_item = OrderItem.objects.filter(
            order__user=request.user,
            order__status='paid',
            product=product
        ).first()
        if order_item:
            is_purchased = True
            purchased_item_id = order_item.id

        is_wishlisted = Wishlist.objects.filter(user=request.user, product=product).exists()
        user_has_reviewed = Review.objects.filter(user=request.user, product=product).exists()

    user_wishlist_ids = {product.id} if is_wishlisted else set()

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'is_purchased': is_purchased,
        'purchased_item_id': purchased_item_id,
        'is_wishlisted': is_wishlisted,
        'user_has_reviewed': user_has_reviewed,
        'user_wishlist_ids': user_wishlist_ids,
    })


def categories_list_view(request):
    categories = Category.objects.annotate(
        approved_count=Count('products', filter=Q(products__status='approved'))
    )
    return render(request, 'marketplace/categories_list.html', {'categories': categories})


def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, status='approved').select_related('seller', 'category')

    featured_products = products.filter(rating__gte=4.5)[:4]

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    return render(request, 'marketplace/category_detail.html', {
        'category': category,
        'page_obj': page_obj,
        'paginator': paginator,
        'featured_products': featured_products,
        'user_wishlist_ids': user_wishlist_ids,
    })


def sellers_list_view(request):
    sellers = SellerProfile.objects.select_related('user').annotate(
        approved_products_count=Count('products', filter=Q(products__status='approved'))
    ).order_by('-total_sales', '-rating')
    return render(request, 'marketplace/sellers_list.html', {'sellers': sellers})


def seller_profile_view(request, slug):
    seller = get_object_or_404(SellerProfile, slug=slug)
    products = Product.objects.filter(seller=seller, status='approved').select_related('category')
    reviews = Review.objects.filter(product__seller=seller).select_related('product', 'user')

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    return render(request, 'marketplace/seller_profile.html', {
        'seller': seller,
        'products': products,
        'reviews': reviews,
        'user_wishlist_ids': user_wishlist_ids,
    })


def search_view(request):
    query = request.GET.get('q', '').strip()
    products = Product.objects.none()

    if query:
        products = Product.objects.filter(
            status='approved'
        ).filter(
            Q(title__icontains=query) |
            Q(short_description__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query) |
            Q(category__name__icontains=query) |
            Q(seller__store_name__icontains=query)
        ).select_related('seller', 'category').distinct()

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        user_wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    return render(request, 'marketplace/search.html', {
        'query': query,
        'products': products,
        'user_wishlist_ids': user_wishlist_ids,
    })


@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product', 'product__seller', 'product__category')
    user_wishlist_ids = set(w.product_id for w in wishlist_items)
    return render(request, 'marketplace/wishlist.html', {
        'wishlist_items': wishlist_items,
        'user_wishlist_ids': user_wishlist_ids,
    })


def wishlist_toggle_view(request, product_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'login_required': True,
            'redirect_url': f"/login/?next=/marketplace/",
            'error': "Sevimlilarga saqlash uchun avval tizimga kiring."
        }, status=401)

    product = get_object_or_404(Product, id=product_id)
    item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        item.delete()
        action = 'removed'
        message = "Mahsulot sevimlilardan olib tashlandi."
    else:
        action = 'added'
        message = "✅ Mahsulot sevimlilarga qo‘shildi."

    total_count = Wishlist.objects.filter(user=request.user).count()
    return JsonResponse({
        'action': action,
        'message': message,
        'total_count': total_count
    })


@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product', 'product__seller', 'product__category')

    subtotal = Decimal('0.00')
    total_discount = Decimal('0.00')

    for item in items:
        subtotal += item.product.price
        if item.product.discount_price and item.product.discount_price < item.product.price:
            total_discount += (item.product.price - item.product.discount_price)

    total = max(Decimal('0.00'), subtotal - total_discount)

    return render(request, 'marketplace/cart.html', {
        'cart': cart,
        'cart_items': items,
        'subtotal': subtotal,
        'total_discount': total_discount,
        'total': total,
    })


def cart_add_view(request, product_id):
    if not request.user.is_authenticated:
        product = Product.objects.filter(id=product_id).first()
        next_path = f"/product/{product.slug}/" if product else "/marketplace/"
        return JsonResponse({
            'login_required': True,
            'redirect_url': f"/login/?next={next_path}",
            'error': "Savatga mahsulot qo‘shish uchun avval tizimga kiring."
        }, status=401)

    product = get_object_or_404(Product, id=product_id)

    already_owned = OrderItem.objects.filter(
        order__user=request.user,
        order__status='paid',
        product=product
    ).exists()
    if already_owned:
        return JsonResponse({
            'owned': True,
            'error': "Siz ushbu mahsulotni avval xarid qilgansiz."
        }, status=400)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    _, created = CartItem.objects.get_or_create(cart=cart, product=product)

    total_items = cart.items.count()
    return JsonResponse({
        'success': True,
        'message': "🛒 Mahsulot savatga qo‘shildi.",
        'total_items': total_items
    })


@login_required
def cart_remove_view(request, item_id):
    cart = get_object_or_404(Cart, user=request.user)
    item = get_object_or_404(CartItem, id=item_id, cart=cart)
    item.delete()
    messages.info(request, "Mahsulot savatdan o‘chirildi.")
    return redirect('cart')


@login_required
def add_review_view(request, slug):
    product = get_object_or_404(Product, slug=slug)

    has_purchased = OrderItem.objects.filter(
        order__user=request.user,
        order__status='paid',
        product=product
    ).exists()

    if not has_purchased and not request.user.is_staff:
        messages.error(request, "Faqat mahsulotni xarid qilganlar sharh qoldirishi mumkin.")
        return redirect('product_detail', slug=slug)

    if Review.objects.filter(user=request.user, product=product).exists():
        messages.warning(request, "Siz allaqachon ushbu mahsulotga sharh qoldirgansiz.")
        return redirect('product_detail', slug=slug)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 5))
            rating = max(1, min(5, rating))
        except ValueError:
            rating = 5

        comment = request.POST.get('comment', '').strip()
        if comment:
            Review.objects.create(
                product=product,
                user=request.user,
                rating=rating,
                comment=comment,
                is_verified_purchase=True
            )
            product.update_rating_stats()

            Notification.objects.create(
                recipient=product.seller.user,
                title="Yangi sharh",
                message=f"⭐ {request.user.username} «{product.title}» mahsulotingizga {rating} yulduzli sharh qoldirdi.",
                notification_type='review',
                link=f"/product/{product.slug}/"
            )

            messages.success(request, "Sharhingiz muvaffaqiyatli qabul qilindi!")
        else:
            messages.error(request, "Sharh matnini kiritish majburiy.")

    return redirect('product_detail', slug=slug)
