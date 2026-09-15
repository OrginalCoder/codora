from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/single/<slug:slug>/', views.checkout_single_view, name='checkout_single'),
    path('checkout/free/<slug:slug>/', views.direct_free_checkout_view, name='direct_free_checkout'),
    path('checkout/apply-coupon/', views.apply_coupon_view, name='apply_coupon'),
    path('checkout/process/', views.process_checkout_view, name='process_checkout'),
    path('checkout/success/<int:order_id>/', views.order_success_view, name='order_success'),
    path('library/', views.library_view, name='library'),
    path('download/<int:order_item_id>/', views.download_product_view, name='download_product'),
]
