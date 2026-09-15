import io
import shutil
import tempfile
import zipfile
from decimal import Decimal
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.marketplace.models import Category, Product, ProductFile, Cart, CartItem
from apps.accounts.models import SellerProfile
from apps.orders.models import Order, OrderItem, Coupon
from apps.notifications.models import Notification


class OrderAndDownloadSecurityTests(TestCase):
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
        self.seller_user = User.objects.create_user(username='seller_user', password='password123')
        self.seller = SellerProfile.objects.create(
            user=self.seller_user,
            store_name='Alpha Studio',
            card_number='8600 1234 5678 9012',
            card_holder='Rustam Aliyev',
            bank_name='TBC Bank'
        )
        self.category = Category.objects.create(name='Code', icon='💻')

        self.product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            title='Secure Script',
            short_description='Safe script',
            description='Script details',
            price=Decimal('50.00'),
            status='approved',
            version='1.0.0'
        )

        self.free_product = Product.objects.create(
            seller=self.seller,
            category=self.category,
            title='Free Open Source Tool',
            short_description='Free tool',
            description='Tool details',
            price=Decimal('0.00'),
            is_free=True,
            status='approved',
            version='1.0.0'
        )

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('main.py', 'print("Hello from secure file")')
        buf.seek(0)

        self.file_asset = ProductFile.objects.create(
            product=self.product,
            file=ContentFile(buf.getvalue(), name='secure-script-v1.0.0.zip'),
            version='1.0.0'
        )

        self.free_file_asset = ProductFile.objects.create(
            product=self.free_product,
            file=ContentFile(buf.getvalue(), name='free-tool-v1.0.0.zip'),
            version='1.0.0'
        )

        self.buyer_user = User.objects.create_user(username='buyer_user', password='password123')
        self.other_user = User.objects.create_user(username='other_user', password='password123')

        self.coupon = Coupon.objects.create(
            code='SAVE10',
            discount_percent=10,
            min_purchase=Decimal('20.00'),
            is_active=True
        )

    def _make_receipt_file(self, name='receipt.png'):
        img = Image.new('RGB', (100, 100), color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')

    def test_coupon_validation(self):
        valid, _ = self.coupon.is_valid(Decimal('50.00'))
        self.assertTrue(valid)
        discount = self.coupon.calculate_discount(Decimal('50.00'))
        self.assertEqual(discount, Decimal('5.00'))

        valid_low, _ = self.coupon.is_valid(Decimal('10.00'))
        self.assertFalse(valid_low)

    def test_checkout_requires_receipt_for_paid_product(self):
        self.client.login(username='buyer_user', password='password123')
        cart = Cart.objects.create(user=self.buyer_user)
        CartItem.objects.create(cart=cart, product=self.product)

        response = self.client.post('/checkout/process/', {
            'coupon_code': 'SAVE10'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'To‘lov cheki faylini yuklash majburiy')
        self.assertFalse(Order.objects.filter(user=self.buyer_user).exists())

    def test_checkout_rejects_invalid_receipt_file(self):
        self.client.login(username='buyer_user', password='password123')
        cart = Cart.objects.create(user=self.buyer_user)
        CartItem.objects.create(cart=cart, product=self.product)

        bad_receipt = SimpleUploadedFile('invoice.exe', b'malicious binary', content_type='application/octet-stream')
        response = self.client.post('/checkout/process/', {
            'coupon_code': 'SAVE10',
            'receipt': bad_receipt
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chek faqat rasm yoki PDF formatida')
        self.assertFalse(Order.objects.filter(user=self.buyer_user).exists())

    def test_p2p_checkout_verification_and_approval_flow(self):
        self.client.login(username='buyer_user', password='password123')
        cart = Cart.objects.create(user=self.buyer_user)
        CartItem.objects.create(cart=cart, product=self.product)

        receipt = self._make_receipt_file('my_chek.png')
        response = self.client.post('/checkout/process/', {
            'coupon_code': 'SAVE10',
            'buyer_note': 'To‘lovchi Ali',
            'receipt': receipt
        })
        self.assertEqual(response.status_code, 302)

        order = Order.objects.filter(user=self.buyer_user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'pending_verification')
        self.assertEqual(order.final_amount, Decimal('45.00'))
        self.assertEqual(order.buyer_note, 'To‘lovchi Ali')
        self.assertTrue(bool(order.receipt_image))
        self.assertEqual(cart.items.count(), 0)

        seller_notif = Notification.objects.filter(recipient=self.seller_user, notification_type='sale').first()
        self.assertIsNotNone(seller_notif)
        self.assertIn('Yangi to‘lov cheki', seller_notif.title)

        order_item = order.items.first()
        blocked_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(blocked_res.status_code, 403)

        self.client.login(username='seller_user', password='password123')
        approve_res = self.client.post(f'/dashboard/orders/{order.id}/approve/', follow=True)
        self.assertEqual(approve_res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.seller.refresh_from_db()
        self.assertEqual(self.seller.balance, Decimal('45.00'))
        self.assertEqual(self.seller.total_earnings, Decimal('45.00'))
        self.assertEqual(self.seller.total_sales, 1)

        buyer_notif = Notification.objects.filter(recipient=self.buyer_user, notification_type='approval').first()
        self.assertIsNotNone(buyer_notif)
        self.assertIn('tasdiqlandi', buyer_notif.title)

        self.client.login(username='buyer_user', password='password123')
        download_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(download_res.status_code, 200)
        self.assertIn(download_res['Content-Type'], ['application/zip', 'application/x-zip-compressed'])

        order_item.refresh_from_db()
        self.assertEqual(order_item.download_count, 1)

        self.client.logout()
        unauth_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(unauth_res.status_code, 302)

        self.client.login(username='other_user', password='password123')
        forbidden_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(forbidden_res.status_code, 403)

    def test_p2p_checkout_rejection_flow(self):
        self.client.login(username='buyer_user', password='password123')
        receipt = self._make_receipt_file('bad_chek.png')
        response = self.client.post('/checkout/process/', {
            'single_product_id': self.product.id,
            'receipt': receipt
        })
        self.assertEqual(response.status_code, 302)

        order = Order.objects.filter(user=self.buyer_user).first()
        self.assertEqual(order.status, 'pending_verification')

        self.client.login(username='seller_user', password='password123')
        reject_res = self.client.post(f'/dashboard/orders/{order.id}/reject/', {
            'rejection_reason': 'Pul tushmadi, qayta tekshiring'
        }, follow=True)
        self.assertEqual(reject_res.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, 'rejected')
        self.assertEqual(order.rejection_reason, 'Pul tushmadi, qayta tekshiring')

        buyer_notif = Notification.objects.filter(recipient=self.buyer_user, notification_type='rejection').first()
        self.assertIsNotNone(buyer_notif)
        self.assertIn('rad etildi', buyer_notif.title)

        order_item = order.items.first()
        self.client.login(username='buyer_user', password='password123')
        download_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(download_res.status_code, 403)

    def test_free_product_direct_checkout(self):
        self.client.login(username='buyer_user', password='password123')
        res = self.client.get(f'/checkout/free/{self.free_product.slug}/', follow=True)
        self.assertEqual(res.status_code, 200)

        order = Order.objects.filter(user=self.buyer_user, payment_method='free').first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'paid')
        self.assertEqual(order.final_amount, Decimal('0.00'))

        order_item = order.items.first()
        download_res = self.client.get(f'/download/{order_item.id}/')
        self.assertEqual(download_res.status_code, 200)

