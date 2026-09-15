import shutil
import tempfile
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User


class AccountsSecurityTests(TestCase):
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
            username='safe_user',
            email='safe@codora.uz',
            password='Password123'
        )

    def test_registration_password_strength_rejected(self):
        res = self.client.post('/register/', {
            'first_name': 'Test',
            'username': 'weak_user',
            'email': 'weak@codora.uz',
            'password': '123',
            'password_confirm': '123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'kamida 8 ta belgi')
        self.assertFalse(User.objects.filter(username='weak_user').exists())

    def test_registration_password_without_letter_or_digit(self):
        res = self.client.post('/register/', {
            'first_name': 'Test',
            'username': 'only_letters',
            'email': 'letters@codora.uz',
            'password': 'abcdefghij',
            'password_confirm': 'abcdefghij'
        })
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'kamida bitta harf va bitta raqam')
        self.assertFalse(User.objects.filter(username='only_letters').exists())

    def test_successful_registration_and_otp_verification(self):
        res = self.client.post('/register/', {
            'first_name': 'Valid',
            'username': 'valid_user',
            'email': 'valid@codora.uz',
            'password': 'ComplexPassword2026',
            'password_confirm': 'ComplexPassword2026'
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, '/verify-email/')
        self.assertFalse(User.objects.filter(username='valid_user').exists())

        from apps.accounts.models import EmailVerification
        verification = EmailVerification.objects.filter(email='valid@codora.uz').first()
        self.assertIsNotNone(verification)
        self.assertEqual(len(verification.code), 6)

        verify_page = self.client.get('/verify-email/')
        self.assertEqual(verify_page.status_code, 200)
        self.assertContains(verify_page, 'Pochtani tasdiqlang')

        wrong_res = self.client.post('/verify-email/', {'code': '000000'})
        self.assertEqual(wrong_res.status_code, 200)
        self.assertContains(wrong_res, 'Tasdiqlash kodi noto‘g‘ri')
        self.assertFalse(User.objects.filter(username='valid_user').exists())

        correct_res = self.client.post('/verify-email/', {'code': verification.code})
        self.assertEqual(correct_res.status_code, 302)
        self.assertEqual(correct_res.url, '/')

        self.assertTrue(User.objects.filter(username='valid_user').exists())
        created_user = User.objects.get(username='valid_user')
        self.assertEqual(created_user.first_name, 'Valid')
        self.assertTrue(created_user.check_password('ComplexPassword2026'))

    def test_verify_email_expired_code_rejected(self):
        from apps.accounts.models import EmailVerification
        from django.utils import timezone
        from datetime import timedelta

        self.client.post('/register/', {
            'first_name': 'Expired',
            'username': 'expired_user',
            'email': 'expired@codora.uz',
            'password': 'ComplexPassword2026',
            'password_confirm': 'ComplexPassword2026'
        })

        verification = EmailVerification.objects.filter(email='expired@codora.uz').first()
        verification.expires_at = timezone.now() - timedelta(minutes=1)
        verification.save()

        res = self.client.post('/verify-email/', {'code': verification.code})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'muddati tugagan')
        self.assertFalse(User.objects.filter(username='expired_user').exists())

    def test_resend_verification_code_cooldown(self):
        from apps.accounts.models import EmailVerification

        self.client.post('/register/', {
            'first_name': 'Resender',
            'username': 'resend_user',
            'email': 'resend@codora.uz',
            'password': 'ComplexPassword2026',
            'password_confirm': 'ComplexPassword2026'
        })

        verification = EmailVerification.objects.filter(email='resend@codora.uz').first()
        old_code = verification.code

        res1 = self.client.post('/resend-code/', follow=True)
        self.assertEqual(res1.status_code, 200)
        self.assertContains(res1, '60 soniya kuting')

        session = self.client.session
        session['last_otp_sent_at'] = 0
        session.save()

        res2 = self.client.post('/resend-code/', follow=True)
        self.assertEqual(res2.status_code, 200)
        self.assertContains(res2, 'Yangi 6 xonali tasdiqlash kodi')

        verification.refresh_from_db()
        self.assertNotEqual(verification.code, old_code)

    def test_login_brute_force_protection(self):
        for _ in range(4):
            res = self.client.post('/login/', {
                'username': 'safe_user',
                'password': 'wrong_password'
            })
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, 'Qolgan urinishlar')

        res_fifth = self.client.post('/login/', {
            'username': 'safe_user',
            'password': 'wrong_password'
        })
        self.assertEqual(res_fifth.status_code, 200)
        self.assertContains(res_fifth, '15 daqiqaga bloklandi')

        res_locked = self.client.post('/login/', {
            'username': 'safe_user',
            'password': 'Password123'
        })
        self.assertEqual(res_locked.status_code, 200)
        self.assertContains(res_locked, 'vaqtincha bloklandi')

    def test_profile_settings_update(self):
        self.client.login(username='safe_user', password='Password123')
        res = self.client.post('/settings/', {
            'form_type': 'profile_info',
            'username': 'safe_user_updated',
            'first_name': 'Ali',
            'last_name': 'Valiyev',
            'email': 'ali_new@codora.uz',
            'phone': '+998901234567',
            'bio': 'Senior Software Engineer'
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'safe_user_updated')
        self.assertEqual(self.user.first_name, 'Ali')
        self.assertEqual(self.user.last_name, 'Valiyev')
        self.assertEqual(self.user.email, 'ali_new@codora.uz')
        self.assertEqual(self.user.profile.phone, '+998901234567')
        self.assertEqual(self.user.profile.bio, 'Senior Software Engineer')

    def test_profile_username_duplicate_rejected(self):
        User.objects.create_user(username='other_user', email='other@codora.uz', password='Password123')
        self.client.login(username='safe_user', password='Password123')
        res = self.client.post('/settings/', {
            'form_type': 'profile_info',
            'username': 'other_user',
            'first_name': 'Ali',
            'email': 'safe@codora.uz',
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'allaqachon band qilingan')

    def test_profile_view_accessible(self):
        self.client.login(username='safe_user', password='Password123')
        res = self.client.get('/profile/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'safe_user')

    def test_unverified_user_login_redirects_to_verify_email(self):
        self.client.post('/register/', {
            'first_name': 'Pending',
            'username': 'pending_user',
            'email': 'pending@codora.uz',
            'password': 'ComplexPassword2026',
            'password_confirm': 'ComplexPassword2026'
        })
        self.assertFalse(User.objects.filter(username='pending_user').exists())

        fresh_client = Client()
        login_res = fresh_client.post('/login/', {
            'username': 'pending_user',
            'password': 'ComplexPassword2026'
        })
        self.assertEqual(login_res.status_code, 302)
        self.assertEqual(login_res.url, '/verify-email/')

        verify_res = fresh_client.get('/verify-email/')
        self.assertEqual(verify_res.status_code, 200)
        self.assertContains(verify_res, 'Pochtani tasdiqlang')

