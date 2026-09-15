import io
import shutil
import tempfile
from PIL import Image
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import SellerProfile
from apps.marketplace.models import Category, Product


class DashboardUploadValidationTests(TestCase):
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
        self.user = User.objects.create_user(
            username='seller_dev',
            email='seller@codora.uz',
            password='Password123'
        )
        self.seller = SellerProfile.objects.create(
            user=self.user,
            store_name='DevStore',
            is_verified=True
        )
        self.category = Category.objects.create(
            name='Telegram Botlar',
            slug='telegram-botlar'
        )

    def test_product_create_invalid_file_extension_rejected(self):
        self.client.login(username='seller_dev', password='Password123')
        bad_file = SimpleUploadedFile('script.exe', b'bad executable content', content_type='application/x-msdownload')
        
        img = Image.new('RGB', (50, 50), color='red')
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG')
        img_io.seek(0)
        thumb = SimpleUploadedFile('thumb.jpg', img_io.getvalue(), content_type='image/jpeg')

        res = self.client.post('/dashboard/products/create/', {
            'title': 'Test Malware Product',
            'category': self.category.id,
            'price': '50000',
            'short_description': 'Short description of product',
            'description': 'Full description of product here with more details',
            'version': '1.0.0',
            'thumbnail': thumb,
            'product_file': bad_file
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'xavfsiz arxiv')
        self.assertFalse(Product.objects.filter(title='Test Malware Product').exists())

    def test_product_create_valid_files_accepted(self):
        self.client.login(username='seller_dev', password='Password123')
        good_file = SimpleUploadedFile('bot_source.zip', b'PK\x03\x04test zip content', content_type='application/zip')
        
        img = Image.new('RGB', (50, 50), color='green')
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)
        thumb = SimpleUploadedFile('thumb.png', img_io.getvalue(), content_type='image/png')

        res = self.client.post('/dashboard/products/create/', {
            'title': 'Telegram AI Bot Pro',
            'category': self.category.id,
            'price': '85000',
            'short_description': 'Short description of product',
            'description': 'Full description of product here with more details',
            'version': '1.0.0',
            'thumbnail': thumb,
            'product_file': good_file
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(Product.objects.filter(title='Telegram AI Bot Pro').exists())

    def test_seller_settings_asset_validation(self):
        self.client.login(username='seller_dev', password='Password123')
        bad_avatar = SimpleUploadedFile('avatar.txt', b'not an image', content_type='text/plain')

        res = self.client.post('/dashboard/settings/', {
            'store_name': 'DevStore',
            'bio': 'Updated store bio',
            'avatar': bad_avatar
        }, follow=True)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'rasm formatida')

    def test_dashboard_financial_report_view(self):
        self.client.login(username='seller_dev', password='Password123')
        res = self.client.get('/dashboard/wallet/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Moliyaviy hisobot va Daromadlar')
        self.assertContains(res, 'Faol to‘lov kartasi')
