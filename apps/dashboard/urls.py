from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_overview, name='dashboard_overview'),
    path('dashboard/products/', views.dashboard_products, name='dashboard_products'),
    path('dashboard/products/create/', views.dashboard_product_create, name='dashboard_product_create'),
    path('dashboard/products/<int:product_id>/edit/', views.dashboard_product_edit, name='dashboard_product_edit'),
    path('dashboard/products/<int:product_id>/delete/', views.dashboard_product_delete, name='dashboard_product_delete'),
    path('dashboard/orders/', views.dashboard_orders, name='dashboard_orders'),
    path('dashboard/orders/<int:order_id>/approve/', views.dashboard_order_approve, name='dashboard_order_approve'),
    path('dashboard/orders/<int:order_id>/reject/', views.dashboard_order_reject, name='dashboard_order_reject'),
    path('dashboard/wallet/', views.dashboard_wallet, name='dashboard_wallet'),
    path('dashboard/wallet/withdraw/', views.request_withdrawal, name='request_withdrawal'),
    path('dashboard/analytics/', views.dashboard_analytics, name='dashboard_analytics'),
    path('dashboard/reviews/', views.dashboard_reviews, name='dashboard_reviews'),
    path('dashboard/reviews/<int:review_id>/reply/', views.reply_review, name='reply_review'),
    path('dashboard/settings/', views.dashboard_settings, name='dashboard_settings'),
]
