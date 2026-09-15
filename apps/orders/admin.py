from django.contrib import admin
from .models import Order, OrderItem, Coupon, DownloadRecord


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'seller', 'price', 'product_title', 'product_version', 'download_count']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'final_amount', 'status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__username', 'user__email']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['product_title', 'order', 'seller', 'price', 'download_count', 'last_downloaded_at']
    list_filter = ['seller', 'order__status']
    search_fields = ['product_title', 'order__order_number']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percent', 'discount_amount', 'max_uses', 'used_count', 'is_active', 'valid_until']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code']


@admin.register(DownloadRecord)
class DownloadRecordAdmin(admin.ModelAdmin):
    list_display = ['order_item', 'user', 'ip_address', 'downloaded_at']
    list_filter = ['downloaded_at']
    search_fields = ['user__username', 'order_item__product_title']
