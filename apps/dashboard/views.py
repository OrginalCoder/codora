import os
from decimal import Decimal
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count, Q
from apps.accounts.models import SellerProfile, WalletTransaction
from apps.marketplace.models import Product, ProductFile, Category, Review, ProductView
from apps.orders.models import Order, OrderItem
from apps.notifications.models import Notification

ALLOWED_PRODUCT_FILE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.pdf', '.fig'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_PRODUCT_FILE_SIZE = 100 * 1024 * 1024
MAX_THUMBNAIL_SIZE = 5 * 1024 * 1024
MAX_BANNER_SIZE = 10 * 1024 * 1024


def validate_seller_assets(avatar, banner):
    if avatar:
        ext = os.path.splitext(avatar.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, "Do‘kon logotipi faqat rasm formatida (.jpg, .jpeg, .png, .webp) bo‘lishi kerak."
        if avatar.size > MAX_THUMBNAIL_SIZE:
            return False, "Do‘kon logotipi hajmi 5 MB dan oshmasligi kerak."
    if banner:
        ext = os.path.splitext(banner.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, "Do‘kon banneri faqat rasm formatida (.jpg, .jpeg, .png, .webp) bo‘lishi kerak."
        if banner.size > MAX_BANNER_SIZE:
            return False, "Do‘kon banneri hajmi 10 MB dan oshmasligi kerak."
    return True, ""


def validate_product_files(thumb_file, product_file, is_edit=False):
    if thumb_file:
        ext = os.path.splitext(thumb_file.name)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return False, "Muqova (thumbnail) faqat rasm formatida (.jpg, .jpeg, .png, .webp) bo‘lishi kerak."
        if thumb_file.size > MAX_THUMBNAIL_SIZE:
            return False, "Muqova rasmi 5 MB dan oshmasligi kerak."

    if product_file:
        ext = os.path.splitext(product_file.name)[1].lower()
        if ext not in ALLOWED_PRODUCT_FILE_EXTENSIONS:
            return False, "Mahsulot fayli faqat xavfsiz arxiv yoki hujjat formatida (.zip, .rar, .7z, .tar, .pdf, .fig) bo‘lishi shart."
        if product_file.size > MAX_PRODUCT_FILE_SIZE:
            return False, "Mahsulot fayli hajmi 100 MB dan oshmasligi kerak."
    elif not is_edit:
        return False, "Mahsulotning raqamli faylini (ZIP/RAR) yuklash majburiy."

    return True, ""


def get_seller_or_redirect(request):
    if not request.user.is_authenticated:
        return None, redirect('login')
    if not hasattr(request.user, 'seller_profile'):
        return None, redirect('become_seller')
    return request.user.seller_profile, None


@login_required
def dashboard_overview(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    recent_orders = OrderItem.objects.filter(
        seller=seller,
        order__status='paid'
    ).select_related('order', 'order__user').order_by('-order__created_at')[:5]

    total_views = Product.objects.filter(seller=seller).aggregate(total=Sum('views_count'))['total'] or 0
    pending_products_count = Product.objects.filter(seller=seller, status='pending').count()

    return render(request, 'dashboard/overview.html', {
        'seller': seller,
        'active_tab': 'overview',
        'recent_orders': recent_orders,
        'total_views': total_views,
        'pending_products_count': pending_products_count,
    })


@login_required
def dashboard_products(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    products = Product.objects.filter(seller=seller).select_related('category')
    return render(request, 'dashboard/products.html', {
        'seller': seller,
        'active_tab': 'products',
        'products': products,
    })


@login_required
def dashboard_product_create(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    categories = Category.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category_id = request.POST.get('category')
        short_description = request.POST.get('short_description', '').strip()
        description = request.POST.get('description', '').strip()
        price_str = request.POST.get('price', '0').strip()
        discount_price_str = request.POST.get('discount_price', '').strip()
        version = request.POST.get('version', '1.0.0').strip()
        file_format = request.POST.get('file_format', 'ZIP').strip()
        compatibility = request.POST.get('compatibility', '').strip()
        requirements = request.POST.get('requirements', '').strip()
        features = request.POST.get('features', '').strip()
        tags = request.POST.get('tags', '').strip()
        changelog = request.POST.get('changelog', '').strip()

        thumb_file = request.FILES.get('thumbnail')
        prod_file = request.FILES.get('product_file')

        valid, msg = validate_product_files(thumb_file, prod_file, is_edit=False)
        if not valid:
            messages.error(request, msg)
            return render(request, 'dashboard/product_form.html', {
                'seller': seller,
                'active_tab': 'create_product',
                'categories': categories,
                'is_edit': False,
            })

        try:
            price = Decimal(price_str)
        except Exception:
            price = Decimal('0.00')

        discount_price = None
        if discount_price_str:
            try:
                discount_price = Decimal(discount_price_str)
            except Exception:
                pass

        category = Category.objects.filter(id=category_id).first()

        product = Product.objects.create(
            seller=seller,
            category=category,
            title=title,
            short_description=short_description,
            description=description,
            price=price,
            discount_price=discount_price,
            is_free=(price == 0),
            version=version,
            file_format=file_format,
            compatibility=compatibility,
            requirements=requirements,
            features=features,
            tags=tags,
            changelog=changelog,
            status='pending'
        )

        if thumb_file:
            product.thumbnail = thumb_file
            product.save()

        if prod_file:
            ProductFile.objects.create(
                product=product,
                file=prod_file,
                version=version
            )

        messages.success(request, "🎉 Mahsulotingiz moderatsiyaga yuborildi! Tez orada tasdiqlanadi.")
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'seller': seller,
        'active_tab': 'create_product',
        'categories': categories,
        'is_edit': False,
    })


@login_required
def dashboard_product_edit(request, product_id):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    product = get_object_or_404(Product, id=product_id, seller=seller)
    categories = Category.objects.all()

    if request.method == 'POST':
        thumb_file = request.FILES.get('thumbnail')
        prod_file = request.FILES.get('product_file')

        valid, msg = validate_product_files(thumb_file, prod_file, is_edit=True)
        if not valid:
            messages.error(request, msg)
            return render(request, 'dashboard/product_form.html', {
                'seller': seller,
                'active_tab': 'products',
                'product': product,
                'categories': categories,
                'is_edit': True,
            })

        product.title = request.POST.get('title', '').strip()
        category_id = request.POST.get('category')
        product.category = Category.objects.filter(id=category_id).first()
        product.short_description = request.POST.get('short_description', '').strip()
        product.description = request.POST.get('description', '').strip()

        price_str = request.POST.get('price', '0').strip()
        discount_price_str = request.POST.get('discount_price', '').strip()
        try:
            product.price = Decimal(price_str)
            product.is_free = (product.price == 0)
        except Exception:
            pass

        if discount_price_str:
            try:
                product.discount_price = Decimal(discount_price_str)
            except Exception:
                product.discount_price = None
        else:
            product.discount_price = None

        product.version = request.POST.get('version', '1.0.0').strip()
        product.file_format = request.POST.get('file_format', 'ZIP').strip()
        product.compatibility = request.POST.get('compatibility', '').strip()
        product.requirements = request.POST.get('requirements', '').strip()
        product.features = request.POST.get('features', '').strip()
        product.tags = request.POST.get('tags', '').strip()
        product.changelog = request.POST.get('changelog', '').strip()

        if thumb_file:
            product.thumbnail = thumb_file

        if prod_file:
            if hasattr(product, 'file_asset'):
                product.file_asset.file = prod_file
                product.file_asset.version = product.version
                product.file_asset.save()
            else:
                ProductFile.objects.create(
                    product=product,
                    file=prod_file,
                    version=product.version
                )

        product.status = 'pending'
        product.save()

        messages.success(request, "Mahsulot yangilandi va moderatsiyaga qayta yuborildi.")
        return redirect('dashboard_products')

    return render(request, 'dashboard/product_form.html', {
        'seller': seller,
        'active_tab': 'products',
        'product': product,
        'categories': categories,
        'is_edit': True,
    })


@login_required
def dashboard_product_delete(request, product_id):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    product = get_object_or_404(Product, id=product_id, seller=seller)
    if request.method == 'POST':
        product.delete()
        messages.info(request, "Mahsulot o‘chirildi.")

    return redirect('dashboard_products')


@login_required
def dashboard_orders(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    orders = Order.objects.filter(
        seller=seller
    ).select_related('user').prefetch_related('items', 'items__product').order_by('-created_at')

    status_filter = request.GET.get('status', 'all')
    if status_filter in ['pending_verification', 'paid', 'rejected']:
        orders = orders.filter(status=status_filter)

    pending_count = Order.objects.filter(seller=seller, status='pending_verification').count()
    paid_count = Order.objects.filter(seller=seller, status='paid').count()

    return render(request, 'dashboard/orders.html', {
        'seller': seller,
        'active_tab': 'orders',
        'orders': orders,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'paid_count': paid_count,
    })


@login_required
def dashboard_order_approve(request, order_id):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    order = get_object_or_404(Order, id=order_id, seller=seller)
    if order.status != 'paid':
        with transaction.atomic():
            order.status = 'paid'
            order.save(update_fields=['status'])

            for item in order.items.all():
                if item.product:
                    item.product.sales_count += 1
                    item.product.save(update_fields=['sales_count'])

            seller.total_sales += 1
            seller.balance += order.final_amount
            seller.total_earnings += order.final_amount
            seller.save(update_fields=['total_sales', 'balance', 'total_earnings'])

            WalletTransaction.objects.create(
                seller=seller,
                transaction_type='sale',
                amount=order.final_amount,
                status='completed',
                description=f"To‘g‘ridan-to‘g‘ri to‘lov tasdiqlandi (#{order.order_number})"
            )

            product_names = ", ".join(item.product_title for item in order.items.all())
            Notification.objects.create(
                recipient=order.user,
                title="To‘lovingiz tasdiqlandi!",
                message=f"🎉 «{seller.store_name}» sotuvchisi to‘lovingizni tasdiqladi (#{order.order_number}). «{product_names}» mahsulotini «Xaridlarim» bo‘limidan yuklab olishingiz mumkin.",
                notification_type='approval',
                link="/library/"
            )

        messages.success(request, f"Buyurtma #{order.order_number} to‘lovi tasdiqlandi va xaridorga yuklab olish ochildi.")

    return redirect('dashboard_orders')


@login_required
def dashboard_order_reject(request, order_id):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    order = get_object_or_404(Order, id=order_id, seller=seller)
    if request.method == 'POST':
        reason = request.POST.get('rejection_reason', '').strip()
        order.status = 'rejected'
        order.rejection_reason = reason
        order.save(update_fields=['status', 'rejection_reason'])

        Notification.objects.create(
            recipient=order.user,
            title="To‘lov cheki rad etildi",
            message=f"⚠️ #{order.order_number} raqamli buyurtma uchun to‘lov cheki «{seller.store_name}» tomonidan rad etildi." + (f" Sabab: {reason}" if reason else ""),
            notification_type='rejection',
            link="/library/"
        )

        messages.warning(request, f"Buyurtma #{order.order_number} rad etildi.")

    return redirect('dashboard_orders')


@login_required
def dashboard_wallet(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    paid_items = OrderItem.objects.filter(
        seller=seller,
        order__status='paid'
    ).select_related('order', 'order__user', 'product')

    month_revenue = paid_items.filter(order__created_at__gte=start_of_month).aggregate(tot=Sum('price'))['tot'] or Decimal('0.00')
    today_revenue = paid_items.filter(order__created_at__gte=start_of_today).aggregate(tot=Sum('price'))['tot'] or Decimal('0.00')

    transactions = WalletTransaction.objects.filter(seller=seller).order_by('-created_at')

    products = Product.objects.filter(seller=seller)
    top_earning_products = []
    for p in products:
        p_revenue = paid_items.filter(product=p).aggregate(tot=Sum('price'))['tot'] or Decimal('0.00')
        if p_revenue > 0 or p.sales_count > 0:
            p.total_revenue = p_revenue
            top_earning_products.append(p)
    top_earning_products.sort(key=lambda x: x.total_revenue, reverse=True)

    return render(request, 'dashboard/wallet.html', {
        'seller': seller,
        'active_tab': 'wallet',
        'transactions': transactions,
        'month_revenue': month_revenue,
        'today_revenue': today_revenue,
        'top_earning_products': top_earning_products[:5],
    })


@login_required
def request_withdrawal(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir
    return redirect('dashboard_wallet')


@login_required
def dashboard_analytics(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    period = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30

    since_date = timezone.now() - timedelta(days=days)

    views_in_period = ProductView.objects.filter(
        product__seller=seller,
        viewed_at__gte=since_date
    ).count()

    sales_in_period = OrderItem.objects.filter(
        seller=seller,
        order__status='paid',
        order__created_at__gte=since_date
    )

    period_sales_count = sales_in_period.count()
    period_revenue = sales_in_period.aggregate(total=Sum('price'))['total'] or Decimal('0.00')

    conversion_rate = 0.0
    if views_in_period > 0:
        conversion_rate = round((period_sales_count / views_in_period) * 100, 1)

    chart_points = 7 if days <= 7 else (14 if days <= 30 else 12)
    chart_labels = []
    chart_data = []

    step_days = max(1, days // chart_points)
    for i in range(chart_points):
        d_start = timezone.now() - timedelta(days=(chart_points - i) * step_days)
        d_end = d_start + timedelta(days=step_days)
        cnt = ProductView.objects.filter(
            product__seller=seller,
            viewed_at__gte=d_start,
            viewed_at__lt=d_end
        ).count()
        chart_labels.append(d_start.strftime("%d.%m"))
        chart_data.append(cnt)

    products = Product.objects.filter(seller=seller)
    product_stats = []
    for p in products:
        prod_revenue = OrderItem.objects.filter(
            product=p,
            order__status='paid'
        ).aggregate(tot=Sum('price'))['tot'] or Decimal('0.00')
        p.total_product_revenue = prod_revenue
        product_stats.append(p)

    return render(request, 'dashboard/analytics.html', {
        'seller': seller,
        'active_tab': 'analytics',
        'period': str(days),
        'period_views': views_in_period,
        'period_sales': period_sales_count,
        'period_revenue': period_revenue,
        'conversion_rate': conversion_rate,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'product_stats': product_stats,
    })


@login_required
def dashboard_reviews(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    reviews = Review.objects.filter(product__seller=seller).select_related('product', 'user')

    return render(request, 'dashboard/reviews.html', {
        'seller': seller,
        'active_tab': 'reviews',
        'reviews': reviews,
    })


@login_required
def reply_review(request, review_id):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    review = get_object_or_404(Review, id=review_id, product__seller=seller)
    if request.method == 'POST':
        reply_text = request.POST.get('seller_reply', '').strip()
        if reply_text:
            review.seller_reply = reply_text
            review.seller_replied_at = timezone.now()
            review.save(update_fields=['seller_reply', 'seller_replied_at'])
            messages.success(request, "Mijoz sharhiga javob yuborildi.")

    return redirect('dashboard_reviews')


@login_required
def dashboard_settings(request):
    seller, redir = get_seller_or_redirect(request)
    if redir:
        return redir

    if request.method == 'POST':
        seller.store_name = request.POST.get('store_name', '').strip()
        seller.bio = request.POST.get('bio', '').strip()
        seller.telegram = request.POST.get('telegram', '').strip()
        seller.github = request.POST.get('github', '').strip()
        seller.website = request.POST.get('website', '').strip()
        seller.card_number = request.POST.get('card_number', '').strip()
        seller.card_holder = request.POST.get('card_holder', '').strip()
        seller.bank_name = request.POST.get('bank_name', '').strip()

        if 'avatar' in request.FILES or 'banner' in request.FILES:
            valid, msg = validate_seller_assets(request.FILES.get('avatar'), request.FILES.get('banner'))
            if not valid:
                messages.error(request, msg)
                return redirect('dashboard_settings')

        if 'avatar' in request.FILES:
            seller.avatar = request.FILES['avatar']
        if 'banner' in request.FILES:
            seller.banner = request.FILES['banner']

        seller.save()
        messages.success(request, "Do‘kon sozlamalari muvaffaqiyatli saqlandi.")
        return redirect('dashboard_settings')

    return render(request, 'dashboard/settings.html', {
        'seller': seller,
        'active_tab': 'settings',
    })
