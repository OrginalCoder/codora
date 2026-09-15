import uuid
from decimal import Decimal
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from apps.marketplace.models import Product
from apps.accounts.models import SellerProfile


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    min_purchase = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_uses = models.PositiveIntegerField(default=100)
    used_count = models.PositiveIntegerField(default=0)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, amount):
        if not self.is_active:
            return False, "Promo-kod faol emas."
        if self.valid_until and timezone.now() > self.valid_until:
            return False, "Promo-kodning amal qilish muddati tugagan."
        if self.used_count >= self.max_uses:
            return False, "Ushbu promo-koddan foydalanish limiti tugagan."
        if amount < self.min_purchase:
            return False, f"Minimal xarid summasi: {self.min_purchase:,.0f} so‘m bo‘lishi kerak."
        return True, "Promo-kod muvaffaqiyatli qo‘llandi."

    def calculate_discount(self, amount):
        valid, _ = self.is_valid(amount)
        if not valid:
            return Decimal('0.00')
        if self.discount_percent > 0:
            discount = (Decimal(str(self.discount_percent)) / Decimal('100')) * amount
        else:
            discount = self.discount_amount
        return min(discount, amount)

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} (-{self.discount_percent}% / -{self.discount_amount:,.0f} so‘m)"


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending_verification', "Chek tekshirilmoqda"),
        ('paid', "Tasdiqlangan"),
        ('rejected', "Rad etilgan"),
        ('cancelled', "Bekor qilindi"),
    ]

    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    seller = models.ForeignKey(SellerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='seller_direct_orders')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending_verification')
    payment_method = models.CharField(max_length=50, default='direct_card')
    payment_reference = models.CharField(max_length=100, blank=True)
    receipt_image = models.ImageField(upload_to='receipts/', blank=True, null=True)
    receipt_uploaded_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    buyer_note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"CDR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Buyurtma #{self.order_number} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, related_name='order_items')
    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='seller_orders')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_title = models.CharField(max_length=200)
    product_version = models.CharField(max_length=50, default='1.0.0')
    download_count = models.PositiveIntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.product_title} ({self.price:,.0f} so‘m)"

    @property
    def has_file(self):
        return bool(self.product and hasattr(self.product, 'file_asset') and self.product.file_asset.file)


class DownloadRecord(models.Model):
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']

    def __str__(self):
        return f"{self.user.username} - {self.order_item.product_title} ({self.downloaded_at.strftime('%Y-%m-%d %H:%M')})"


@receiver(post_delete, sender=Order)
def auto_delete_order_receipt_on_delete(sender, instance, **kwargs):
    if instance.receipt_image:
        try:
            instance.receipt_image.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=Order)
def auto_delete_order_receipt_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_order = Order.objects.get(pk=instance.pk)
    except Order.DoesNotExist:
        return
    if old_order.receipt_image and old_order.receipt_image != instance.receipt_image:
        try:
            old_order.receipt_image.delete(save=False)
        except Exception:
            pass

