from django.contrib import admin
from .models import Profile, SellerProfile, SellerApplication, WalletTransaction


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']


@admin.register(SellerProfile)
class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ['store_name', 'user', 'rating', 'total_sales', 'balance', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['store_name', 'user__username', 'user__email', 'telegram']
    prepopulated_fields = {'slug': ('store_name',)}


@admin.register(SellerApplication)
class SellerApplicationAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'created_at', 'reviewed_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'user__email']
    actions = ['approve_application', 'reject_application']

    def approve_application(self, request, queryset):
        for app in queryset:
            app.status = 'approved'
            app.save()
            if not hasattr(app.user, 'seller_profile'):
                SellerProfile.objects.create(
                    user=app.user,
                    store_name=app.user.get_full_name() or app.user.username,
                    is_verified=True
                )
    approve_application.short_description = "Tanlangan arizalarni tasdiqlash"

    def reject_application(self, request, queryset):
        queryset.update(status='rejected')
    reject_application.short_description = "Tanlangan arizalarni rad etish"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['seller', 'transaction_type', 'amount', 'status', 'created_at']
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['seller__store_name', 'description']
