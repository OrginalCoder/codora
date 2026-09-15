from django.contrib import admin
from .models import Category, Product, ProductImage, ProductFile, Review, Wishlist, Cart, CartItem, ProductView
from apps.notifications.models import Notification


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductFileInline(admin.StackedInline):
    model = ProductFile
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['icon', 'name', 'slug', 'is_featured', 'order']
    list_editable = ['is_featured', 'order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'seller', 'category', 'price', 'discount_price', 'status', 'sales_count', 'rating', 'created_at']
    list_filter = ['status', 'category', 'is_free', 'created_at']
    search_fields = ['title', 'short_description', 'tags', 'seller__store_name']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProductFileInline, ProductImageInline]
    actions = ['approve_products', 'reject_products', 'suspend_products']

    def approve_products(self, request, queryset):
        for prod in queryset:
            prod.status = 'approved'
            prod.rejection_reason = ''
            prod.save(update_fields=['status', 'rejection_reason'])
            Notification.objects.create(
                recipient=prod.seller.user,
                title="Mahsulotingiz tasdiqlandi",
                message=f"✅ «{prod.title}» mahsulotingiz moderatorlar tomonidan tasdiqlandi va sotuvga chiqarildi!",
                notification_type='approval',
                link=f"/product/{prod.slug}/"
            )
    approve_products.short_description = "Tanlangan mahsulotlarni tasdiqlash (Approve)"

    def reject_products(self, request, queryset):
        for prod in queryset:
            prod.status = 'rejected'
            if not prod.rejection_reason:
                prod.rejection_reason = "Mahsulot platforma sifat standartlariga to‘liq javob bermadi."
            prod.save(update_fields=['status', 'rejection_reason'])
            Notification.objects.create(
                recipient=prod.seller.user,
                title="Mahsulotingiz rad etildi",
                message=f"❌ «{prod.title}» mahsulotingiz rad etildi. Sabab: {prod.rejection_reason}",
                notification_type='rejection',
                link="/dashboard/products/"
            )
    reject_products.short_description = "Tanlangan mahsulotlarni rad etish (Reject)"

    def suspend_products(self, request, queryset):
        queryset.update(status='suspended')
    suspend_products.short_description = "Tanlangan mahsulotlarni to‘xtatish (Suspend)"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__title', 'user__username', 'comment']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'created_at']
    search_fields = ['user__username', 'product__title']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'total_items', 'created_at']


@admin.register(ProductView)
class ProductViewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'ip_address', 'viewed_at']
    list_filter = ['viewed_at']
