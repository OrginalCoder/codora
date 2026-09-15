import os
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404, FileResponse, HttpResponseForbidden
from django.db import transaction
from django.utils import timezone
from .models import Order, OrderItem, Coupon, DownloadRecord
from apps.marketplace.models import Product, Cart, CartItem
from apps.accounts.models import WalletTransaction
from apps.notifications.models import Notification


ALLOWED_RECEIPT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf', '.heic'}
MAX_RECEIPT_SIZE = 5 * 1024 * 1024


def validate_receipt_file(uploaded_file):
    if not uploaded_file:
        return False, "To‘lov cheki faylini yuklash majburiy."
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_RECEIPT_EXTENSIONS:
        return False, "Chek faqat rasm yoki PDF formatida (.jpg, .jpeg, .png, .webp, .pdf, .heic) bo‘lishi kerak."
    if uploaded_file.size > MAX_RECEIPT_SIZE:
        return False, "Chek fayli hajmi 5 MB dan oshmasligi kerak."
    return True, ""


@login_required
def checkout_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    if not cart or not cart.items.exists():
        messages.info(request, "Savatingiz bo‘sh.")
        return redirect('cart')

    items = cart.items.select_related('product', 'product__seller')

    for item in items:
        already_owned = OrderItem.objects.filter(
            order__user=request.user,
            order__status='paid',
            product=item.product
        ).exists()
        if already_owned:
            messages.warning(request, f"«{item.product.title}» mahsulotini siz avval xarid qilgansiz.")
            item.delete()
            return redirect('cart')

    subtotal = Decimal('0.00')
    for item in items:
        subtotal += item.product.effective_price

    coupon_code = request.GET.get('coupon', '').strip().upper()
    discount_amount = Decimal('0.00')
    coupon_valid = False
    coupon_message = ""

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            valid, msg = coupon.is_valid(subtotal)
            coupon_valid = valid
            coupon_message = msg
            if valid:
                discount_amount = coupon.calculate_discount(subtotal)
        else:
            coupon_message = "Bunday promo-kod mavjud emas."

    final_amount = max(Decimal('0.00'), subtotal - discount_amount)
    first_item = items.first()
    seller = first_item.product.seller if first_item else None

    return render(request, 'orders/checkout.html', {
        'items': items,
        'seller': seller,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'final_amount': final_amount,
        'coupon_code': coupon_code if coupon_valid else '',
        'coupon_valid': coupon_valid,
        'coupon_message': coupon_message,
    })


@login_required
def checkout_single_view(request, slug):
    product = get_object_or_404(Product, slug=slug, status='approved')

    already_owned = OrderItem.objects.filter(
        order__user=request.user,
        order__status='paid',
        product=product
    ).exists()
    if already_owned:
        messages.info(request, "Siz ushbu mahsulotni avval xarid qilgansiz.")
        return redirect('library')

    subtotal = product.effective_price

    coupon_code = request.GET.get('coupon', '').strip().upper()
    discount_amount = Decimal('0.00')
    coupon_valid = False
    coupon_message = ""

    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            valid, msg = coupon.is_valid(subtotal)
            coupon_valid = valid
            coupon_message = msg
            if valid:
                discount_amount = coupon.calculate_discount(subtotal)
        else:
            coupon_message = "Bunday promo-kod mavjud emas."

    final_amount = max(Decimal('0.00'), subtotal - discount_amount)

    class MockItem:
        def __init__(self, p):
            self.product = p

    return render(request, 'orders/checkout.html', {
        'items': [MockItem(product)],
        'seller': product.seller,
        'single_product_id': product.id,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'final_amount': final_amount,
        'coupon_code': coupon_code if coupon_valid else '',
        'coupon_valid': coupon_valid,
        'coupon_message': coupon_message,
    })


@login_required
def direct_free_checkout_view(request, slug):
    product = get_object_or_404(Product, slug=slug, status='approved', is_free=True)

    order_item = OrderItem.objects.filter(
        order__user=request.user,
        order__status='paid',
        product=product
    ).first()

    if order_item:
        return redirect('library')

    with transaction.atomic():
        order = Order.objects.create(
            user=request.user,
            seller=product.seller,
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            status='paid',
            payment_method='free'
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            seller=product.seller,
            price=Decimal('0.00'),
            product_title=product.title,
            product_version=product.version
        )

        product.sales_count += 1
        product.save(update_fields=['sales_count'])
        product.seller.total_sales += 1
        product.seller.save(update_fields=['total_sales'])

    messages.success(request, "🎉 Mahsulot shaxsiy kutubxonangizga muvaffaqiyatli qo‘shildi!")
    return redirect('order_success', order_id=order.id)


@login_required
def apply_coupon_view(request):
    if request.method == 'POST':
        code = request.POST.get('coupon_code', '').strip()
        single_product_id = request.POST.get('single_product_id', '')

        if single_product_id:
            product = get_object_or_404(Product, id=single_product_id)
            return redirect(f"/checkout/single/{product.slug}/?coupon={code}")
        else:
            return redirect(f"/checkout/?coupon={code}")

    return redirect('checkout')


@login_required
def process_checkout_view(request):
    if request.method != 'POST':
        return redirect('checkout')

    single_product_id = request.POST.get('single_product_id')
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    buyer_note = request.POST.get('buyer_note', '').strip()

    products_to_buy = []
    seller = None

    if single_product_id:
        product = get_object_or_404(Product, id=single_product_id, status='approved')
        products_to_buy.append(product)
        seller = product.seller
    else:
        cart = Cart.objects.filter(user=request.user).first()
        if not cart or not cart.items.exists():
            messages.error(request, "Savatingiz bo‘sh.")
            return redirect('cart')
        for ci in cart.items.select_related('product', 'product__seller'):
            products_to_buy.append(ci.product)
        if products_to_buy:
            seller = products_to_buy[0].seller

    subtotal = sum(p.effective_price for p in products_to_buy)

    coupon = None
    discount_amount = Decimal('0.00')
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code).first()
        if coupon:
            valid, _ = coupon.is_valid(subtotal)
            if valid:
                discount_amount = coupon.calculate_discount(subtotal)
            else:
                coupon = None

    final_amount = max(Decimal('0.00'), subtotal - discount_amount)
    is_free = final_amount == Decimal('0.00')
    receipt_file = request.FILES.get('receipt') or request.FILES.get('receipt_image')

    if not is_free:
        valid, msg = validate_receipt_file(receipt_file)
        if not valid:
            messages.error(request, msg)
            if single_product_id:
                return redirect(f"/checkout/single/{products_to_buy[0].slug}/")
            return redirect('checkout')

    with transaction.atomic():
        order_status = 'paid' if is_free else 'pending_verification'
        order = Order.objects.create(
            user=request.user,
            seller=seller,
            total_amount=subtotal,
            discount_amount=discount_amount,
            final_amount=final_amount,
            coupon=coupon,
            status=order_status,
            payment_method='free' if is_free else 'direct_card',
            payment_reference=f"P2P-{order_ref()}",
            receipt_image=receipt_file,
            receipt_uploaded_at=timezone.now() if receipt_file else None,
            buyer_note=buyer_note
        )

        if coupon:
            coupon.used_count += 1
            coupon.save(update_fields=['used_count'])

        for prod in products_to_buy:
            OrderItem.objects.create(
                order=order,
                product=prod,
                seller=prod.seller,
                price=prod.effective_price,
                product_title=prod.title,
                product_version=prod.version
            )
            if is_free:
                prod.sales_count += 1
                prod.save(update_fields=['sales_count'])
                if prod.seller:
                    prod.seller.total_sales += 1
                    prod.seller.save(update_fields=['total_sales'])

        if not is_free and seller:
            Notification.objects.create(
                recipient=seller.user,
                title="Yangi to‘lov cheki yuklandi!",
                message=f"🛒 #{order.order_number} raqamli buyurtma uchun xaridor @{request.user.username} to‘lov chekini yukladi ({final_amount:,.0f} so‘m). Iltimos, tekshirib tasdiqlang.",
                notification_type='sale',
                link="/dashboard/orders/"
            )

        if not single_product_id:
            cart = Cart.objects.filter(user=request.user).first()
            if cart:
                cart.items.all().delete()

    if is_free:
        messages.success(request, "🎉 Bepul mahsulot kutubxonangizga qo‘shildi!")
    else:
        messages.success(request, "To‘lov chekingiz yuborildi. Sotuvchi tasdiqlashi bilan mahsulot ochiladi.")

    return redirect('order_success', order_id=order.id)


def order_ref():
    import uuid
    return uuid.uuid4().hex[:8].upper()


@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_success.html', {'order': order})


@login_required
def library_view(request):
    order_items = OrderItem.objects.filter(
        order__user=request.user
    ).select_related('product', 'product__file_asset', 'seller', 'order').order_by('-order__created_at')

    return render(request, 'orders/library.html', {'order_items': order_items})


@login_required
def download_product_view(request, order_item_id):
    order_item = get_object_or_404(
        OrderItem.objects.select_related('order', 'product', 'product__file_asset'),
        id=order_item_id
    )

    if order_item.order.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Sizda ushbu faylni yuklab olish huquqi yo‘q.")

    if order_item.order.status != 'paid':
        return HttpResponseForbidden("Buyurtma uchun to‘lov amalga oshirilmagan.")

    product = order_item.product
    if not product or not hasattr(product, 'file_asset') or not product.file_asset.file:
        raise Http404("Fayl serverda mavjud emas yoki muallif tomonidan yangilanmoqda.")

    file_obj = product.file_asset.file
    try:
        file_path = file_obj.path
        if not os.path.exists(file_path):
            raise Http404("Fayl topilmadi.")
    except NotImplementedError:
        pass

    order_item.download_count += 1
    order_item.save(update_fields=['download_count'])

    DownloadRecord.objects.create(
        order_item=order_item,
        user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
    )

    filename = os.path.basename(file_obj.name)
    safe_name = f"{product.slug}-v{product.version}.zip"

    response = FileResponse(file_obj.open('rb'), as_attachment=True, filename=safe_name)
    return response
