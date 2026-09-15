from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('marketplace/', views.marketplace_view, name='marketplace'),
    path('categories/', views.categories_list_view, name='categories_list'),
    path('category/<slug:slug>/', views.category_detail_view, name='category_detail'),
    path('sellers/', views.sellers_list_view, name='sellers_list'),
    path('seller/<slug:slug>/', views.seller_profile_view, name='seller_profile'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('product/<slug:slug>/review/', views.add_review_view, name='add_review'),
    path('search/', views.search_view, name='search'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.wishlist_toggle_view, name='wishlist_toggle'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.cart_add_view, name='cart_add'),
    path('cart/remove/<int:item_id>/', views.cart_remove_view, name='cart_remove'),
]
