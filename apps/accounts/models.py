from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.text import slugify


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} profili"

    @property
    def display_name(self):
        full_name = self.user.get_full_name()
        return full_name if full_name else self.user.username


class SellerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    store_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='sellers/avatars/', blank=True, null=True)
    banner = models.ImageField(upload_to='sellers/banners/', blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_sales = models.PositiveIntegerField(default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    pending_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=False)
    website = models.URLField(blank=True)
    telegram = models.CharField(max_length=100, blank=True)
    github = models.CharField(max_length=100, blank=True)
    card_number = models.CharField(max_length=30, blank=True)
    card_holder = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.store_name)
            slug = base_slug or f"seller-{self.user.id or 1}"
            counter = 1
            while SellerProfile.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.store_name


class SellerApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', "Ko‘rib chiqilmoqda"),
        ('approved', "Tasdiqlangan"),
        ('rejected', "Rad etilgan"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='seller_applications')
    experience = models.TextField()
    portfolio_url = models.URLField(blank=True)
    motivation = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} arizasi ({self.get_status_display()})"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale', "Sotuv"),
        ('withdrawal', "Yechib olish"),
        ('commission', "Komissiya"),
        ('refund', "Qaytarish"),
    ]
    STATUS_CHOICES = [
        ('pending', "Kutilmoqda"),
        ('completed', "Bajarildi"),
        ('cancelled', "Bekor qilindi"),
    ]

    seller = models.ForeignKey(SellerProfile, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.seller.store_name} - {self.get_transaction_type_display()}: {self.amount:,.0f} so‘m"


class EmailVerification(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    first_name = models.CharField(max_length=150, blank=True)
    username = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=255)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.code}"


@receiver(post_delete, sender=Profile)
def auto_delete_profile_avatar_on_delete(sender, instance, **kwargs):
    if instance.avatar:
        try:
            instance.avatar.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=Profile)
def auto_delete_profile_avatar_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_avatar = Profile.objects.get(pk=instance.pk).avatar
    except Profile.DoesNotExist:
        return
    new_avatar = instance.avatar
    if old_avatar and old_avatar != new_avatar:
        try:
            old_avatar.delete(save=False)
        except Exception:
            pass


@receiver(post_delete, sender=SellerProfile)
def auto_delete_seller_media_on_delete(sender, instance, **kwargs):
    if instance.avatar:
        try:
            instance.avatar.delete(save=False)
        except Exception:
            pass
    if instance.banner:
        try:
            instance.banner.delete(save=False)
        except Exception:
            pass


@receiver(pre_save, sender=SellerProfile)
def auto_delete_seller_media_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_seller = SellerProfile.objects.get(pk=instance.pk)
    except SellerProfile.DoesNotExist:
        return
    if old_seller.avatar and old_seller.avatar != instance.avatar:
        try:
            old_seller.avatar.delete(save=False)
        except Exception:
            pass
    if old_seller.banner and old_seller.banner != instance.banner:
        try:
            old_seller.banner.delete(save=False)
        except Exception:
            pass


