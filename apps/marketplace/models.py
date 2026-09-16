import os
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from apps.accounts.models import SellerProfile


class ProtectedFileSystemStorage(FileSystemStorage):
    @property
    def location(self):
        return os.path.abspath(settings.PROTECTED_MEDIA_ROOT)

    @property
    def base_location(self):
        return settings.PROTECTED_MEDIA_ROOT


protected_storage = ProtectedFileSystemStorage()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    icon = models.CharField(max_length=20, default='📦')
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "category"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.icon} {self.name}"

    @property
    def approved_products_count(self):
        if hasattr(self, 'approved_count'):
            return self.approved_count
        return self.products.filter(status='approved').count()


class Product(models.Model):
    STATUS_CHOICES = [
        ('draft', "Qoralama"),
        ('pending', "Ko‘rib chiqilmoqda"),
        ('approved', "Tasdiqlangan"),
        ('rejected', "Rad etilgan"),
        ('suspended', "To‘xtatilgan"),
    ]

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    short_description = models.CharField(max_length=300)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_free = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    version = models.CharField(max_length=50, default='1.0.0')
    file_format = models.CharField(max_length=100, default='ZIP')
    compatibility = models.CharField(max_length=200, blank=True)
    requirements = models.TextField(blank=True)
    features = models.TextField(blank=True)
    changelog = models.TextField(blank=True)
    documentation = models.TextField(blank=True)
    demo_url = models.URLField(blank=True)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True)
    views_count = models.PositiveIntegerField(default=0)
    sales_count = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    reviews_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug or f"product-{self.seller.id or 1}"
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def effective_price(self):
        if self.is_free:
            return 0.00
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    @property
    def discount_percent(self):
        if self.discount_price and self.price > 0 and self.discount_price < self.price:
            discount = ((self.price - self.discount_price) / self.price) * 100
            return int(round(discount))
        return 0

    @property
    def features_list(self):
        if not self.features:
            return []
        return [f.strip() for f in self.features.split('\n') if f.strip()]

    @property
    def requirements_list(self):
        if not self.requirements:
            return []
        return [r.strip() for r in self.requirements.split('\n') if r.strip()]

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def update_rating_stats(self):
        reviews = self.reviews.all()
        count = reviews.count()
        if count > 0:
            avg = sum(r.rating for r in reviews) / count
            self.rating = round(avg, 2)
            self.reviews_count = count
        else:
            self.rating = 5.00
            self.reviews_count = 0
        self.save(update_fields=['rating', 'reviews_count'])


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.title} rasmi"


class ProductFile(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='file_asset')
    file = models.FileField(storage=protected_storage, upload_to='products/')
    version = models.CharField(max_length=50, default='1.0.0')
    file_size = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.file and not self.file_size:
            try:
                size_bytes = self.file.size
                if size_bytes < 1024:
                    self.file_size = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    self.file_size = f"{size_bytes / 1024:.1f} KB"
                else:
                    self.file_size = f"{size_bytes / (1024 * 1024):.1f} MB"
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.title} fayli (v{self.version})"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], default=5)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=True)
    seller_reply = models.TextField(blank=True)
    seller_replied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.title} ({self.rating}★)"


class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_entries')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.product.title}"


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Savat ({self.user.username if self.user else self.session_key})"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def total_price(self):
        return sum(item.product.effective_price for item in self.items.select_related('product'))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    def __str__(self):
        return f"{self.cart} - {self.product.title}"


class ProductView(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='views_log')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']


@receiver(post_delete, sender=ProductFile)
def auto_delete_product_file_on_delete(sender, instance, **kwargs):
    if instance.file:
        try:
            instance.file.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=ProductFile)
def auto_delete_product_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_file = ProductFile.objects.get(pk=instance.pk).file
    except ProductFile.DoesNotExist:
        return
    new_file = instance.file
    if old_file and old_file != new_file:
        try:
            old_file.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=Product)
def auto_delete_product_thumbnail_on_delete(sender, instance, **kwargs):
    if instance.thumbnail:
        try:
            instance.thumbnail.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=Product)
def auto_delete_product_thumbnail_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_thumb = Product.objects.get(pk=instance.pk).thumbnail
    except Product.DoesNotExist:
        return
    new_thumb = instance.thumbnail
    if old_thumb and old_thumb != new_thumb:
        try:
            old_thumb.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=ProductImage)
def auto_delete_product_image_on_delete(sender, instance, **kwargs):
    if instance.image:
        try:
            instance.image.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=ProductImage)
def auto_delete_product_image_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_img = ProductImage.objects.get(pk=instance.pk).image
    except ProductImage.DoesNotExist:
        return
    new_img = instance.image
    if old_img and old_img != new_img:
        try:
            old_img.delete(save=False)
        except Exception:
            pass

