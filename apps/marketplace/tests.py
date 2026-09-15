import shutil
import tempfile
from decimal import Decimal
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from apps.marketplace.models import Category, Product, Wishlist, Cart, CartItem, Review
from apps.accounts.models import SellerProfile
from apps.orders.models import Order, OrderItem


class MarketplaceComprehensiveTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_media = tempfile.mkdtemp()
        cls._temp_protected = tempfile.mkdtemp()
        cls._override = override_settings(
            MEDIA_ROOT=cls._temp_media,
            PROTECTED_MEDIA_ROOT=cls._temp_protected
        )
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        shutil.rmtree(cls._temp_media, ignore_errors=True)
        shutil.rmtree(cls._temp_protected, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.seller_user = User.objects.create_user(username='test_seller', password='password123')
        self.seller = SellerProfile.objects.create(user=self.seller_user, store_name='Test Store')
        self.category = Category.objects.create(name='Test Category', icon='🤖')
        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            title='Test Product',
            short_description='Short description',
            description='Full description',
            price=Decimal('20.00'),
            status='approved'
        )
        self.buyer_user = User.objects.create_user(username='test_buyer', password='password123')

    def test_home_page_status(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Codora')
        self.assertContains(response, 'Raqamli mahsulotlarni')

    def test_marketplace_page_status(self):
        response = self.client.get('/marketplace/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_product_detail_page(self):
        response = self.client.get(f'/product/{self.product.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')
        self.assertContains(response, 'Test Store')

    def test_categories_pages(self):
        res1 = self.client.get('/categories/')
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, 'Test Category')

        res2 = self.client.get(f'/category/{self.category.slug}/')
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, 'Test Product')

    def test_sellers_pages(self):
        res1 = self.client.get('/sellers/')
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, 'Test Store')

        res2 = self.client.get(f'/seller/{self.seller.slug}/')
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, 'Test Store')

    def test_search_functionality(self):
        response = self.client.get('/search/?q=Test')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Product')

    def test_wishlist_toggle(self):
        self.client.login(username='test_buyer', password='password123')
        response = self.client.post(f'/wishlist/toggle/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Wishlist.objects.filter(user=self.buyer_user, product=self.product).exists())

        response = self.client.post(f'/wishlist/toggle/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Wishlist.objects.filter(user=self.buyer_user, product=self.product).exists())

    def test_guest_cart_and_wishlist_blocked(self):
        res_cart = self.client.post(f'/cart/add/{self.product.id}/')
        self.assertEqual(res_cart.status_code, 401)
        self.assertTrue(res_cart.json().get('login_required'))

        res_cart_view = self.client.get('/cart/')
        self.assertEqual(res_cart_view.status_code, 302)

        res_wish = self.client.post(f'/wishlist/toggle/{self.product.id}/')
        self.assertEqual(res_wish.status_code, 401)
        self.assertTrue(res_wish.json().get('login_required'))

    def test_cart_add_and_remove(self):
        self.client.login(username='test_buyer', password='password123')
        response = self.client.post(f'/cart/add/{self.product.id}/')
        self.assertEqual(response.status_code, 200)
        cart = Cart.objects.get(user=self.buyer_user)
        self.assertEqual(cart.items.count(), 1)

        item = cart.items.first()
        response = self.client.post(f'/cart/remove/{item.id}/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(cart.items.count(), 0)

    def test_seller_dashboard_access(self):
        self.client.login(username='test_buyer', password='password123')
        res_non_seller = self.client.get('/dashboard/')
        self.assertEqual(res_non_seller.status_code, 302)

        self.client.login(username='test_seller', password='password123')
        res_seller = self.client.get('/dashboard/')
        self.assertEqual(res_seller.status_code, 200)
        self.assertContains(res_seller, 'Sotuvchi paneli')

    def test_verified_review_restriction(self):
        self.client.login(username='test_buyer', password='password123')
        res = self.client.post(f'/product/{self.product.slug}/review/', {
            'rating': 5,
            'comment': 'Zo‘r mahsulot!'
        })
        self.assertEqual(res.status_code, 302)
        self.assertFalse(Review.objects.filter(product=self.product, user=self.buyer_user).exists())

        order = Order.objects.create(user=self.buyer_user, total_amount=Decimal('20.00'), final_amount=Decimal('20.00'), status='paid')
        OrderItem.objects.create(order=order, product=self.product, seller=self.seller, price=Decimal('20.00'), product_title=self.product.title)

        res2 = self.client.post(f'/product/{self.product.slug}/review/', {
            'rating': 5,
            'comment': 'Zo‘r mahsulot!'
        })
        self.assertEqual(res2.status_code, 302)
        self.assertTrue(Review.objects.filter(product=self.product, user=self.buyer_user).exists())

    def test_custom_404_handler(self):
        res = self.client.get('/non-existent-url-slug-12345/')
        self.assertEqual(res.status_code, 404)
        self.assertContains(res, 'Bu sahifani topa olmadik', status_code=404)
