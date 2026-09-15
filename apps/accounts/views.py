import os
import re
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from .models import Profile, SellerProfile, SellerApplication, EmailVerification
from .utils import generate_otp_code, send_verification_email
from apps.orders.models import OrderItem
from apps.marketplace.models import Wishlist, Review

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic'}
MAX_AVATAR_SIZE = 5 * 1024 * 1024


def validate_image_file(uploaded_file):
    if not uploaded_file:
        return True, ""
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, "Faqat ruxsat etilgan rasm formatlari (.jpg, .jpeg, .png, .webp, .gif, .heic) qabul qilinadi."
    if uploaded_file.size > MAX_AVATAR_SIZE:
        return False, "Profil rasmi hajmi 5 MB dan oshmasligi kerak."
    return True, ""


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    failed_attempts = request.session.get('login_failed_attempts', 0)
    lockout_time_str = request.session.get('login_lockout_until')

    if lockout_time_str:
        lockout_time = datetime.fromisoformat(lockout_time_str)
        if datetime.now() < lockout_time:
            remaining_minutes = int((lockout_time - datetime.now()).total_seconds() / 60) + 1
            return render(request, 'accounts/login.html', {
                'error': f"Xavfsizlik maqsadida kirish vaqtincha bloklandi. Iltimos, {remaining_minutes} daqiqadan so‘ng qayta urinib ko‘ring."
            })
        else:
            request.session['login_failed_attempts'] = 0
            request.session.pop('login_lockout_until', None)

    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user_obj = None
        if '@' in username_or_email:
            user_by_email = User.objects.filter(email__iexact=username_or_email).first()
            if user_by_email:
                user_obj = authenticate(request, username=user_by_email.username, password=password)
        else:
            user_obj = authenticate(request, username=username_or_email, password=password)

        if user_obj:
            request.session['login_failed_attempts'] = 0
            request.session.pop('login_lockout_until', None)
            login(request, user_obj)
            messages.success(request, f"Xush kelibsiz, {user_obj.first_name or user_obj.username}!")
            next_url = request.GET.get('next') or 'home'
            return redirect(next_url)
        else:
            pending_verification = None
            if '@' in username_or_email:
                pending_verification = EmailVerification.objects.filter(email__iexact=username_or_email, is_verified=False).first()
            else:
                pending_verification = EmailVerification.objects.filter(username__iexact=username_or_email, is_verified=False).first()

            if pending_verification and check_password(password, pending_verification.password_hash):
                request.session['login_failed_attempts'] = 0
                request.session.pop('login_lockout_until', None)

                code = generate_otp_code()
                pending_verification.code = code
                pending_verification.expires_at = timezone.now() + timedelta(minutes=5)
                pending_verification.attempts = 0
                pending_verification.save()

                try:
                    send_verification_email(pending_verification.email, code, pending_verification.first_name)
                except Exception:
                    pass

                request.session['pending_verification_email'] = pending_verification.email
                request.session['last_otp_sent_at'] = datetime.now().timestamp()
                messages.info(request, "Hisobingiz hali tasdiqlanmagan. Elektron pochtangizga yangi 6 xonali tasdiqlash kodi yuborildi.")
                return redirect('verify_email')

            failed_attempts += 1
            request.session['login_failed_attempts'] = failed_attempts
            if failed_attempts >= 5:
                lockout_until = datetime.now() + timedelta(minutes=15)
                request.session['login_lockout_until'] = lockout_until.isoformat()
                return render(request, 'accounts/login.html', {
                    'error': "Xatoliklar soni ko‘payib ketdi. Xavfsizlik yuzasidan tizimga kirish 15 daqiqaga bloklandi."
                })

            remaining = 5 - failed_attempts
            return render(request, 'accounts/login.html', {
                'error': f"Foydalanuvchi nomi yoki parol noto‘g‘ri. (Qolgan urinishlar: {remaining} ta)",
                'username': username_or_email
            })

    return render(request, 'accounts/login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        username = request.POST.get('username', '').strip().lower()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not username or not email or not password:
            return render(request, 'accounts/register.html', {
                'error': "Barcha majburiy maydonlarni to‘ldiring.",
                'first_name': first_name, 'username': username, 'email': email
            })

        if not re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            return render(request, 'accounts/register.html', {
                'error': "Foydalanuvchi nomi 3 dan 30 tagacha lotin harflari, raqamlar va pastki chiziqdan iborat bo‘lishi kerak.",
                'first_name': first_name, 'username': username, 'email': email
            })

        if password != password_confirm:
            return render(request, 'accounts/register.html', {
                'error': "Parollar bir-biriga mos kelmadi.",
                'first_name': first_name, 'username': username, 'email': email
            })

        if len(password) < 8:
            return render(request, 'accounts/register.html', {
                'error': "Parol uzunligi kamida 8 ta belgidan iborat bo‘lishi shart.",
                'first_name': first_name, 'username': username, 'email': email
            })

        if not any(char.isdigit() for char in password) or not any(char.isalpha() for char in password):
            return render(request, 'accounts/register.html', {
                'error': "Parolda kamida bitta harf va bitta raqam ishtirok etishi kerak.",
                'first_name': first_name, 'username': username, 'email': email
            })

        dummy_user = User(username=username, email=email)
        try:
            validate_password(password, dummy_user)
        except ValidationError as e:
            return render(request, 'accounts/register.html', {
                'error': " ".join(e.messages),
                'first_name': first_name, 'username': username, 'email': email
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'accounts/register.html', {
                'error': "Ushbu foydalanuvchi nomi allaqachon band qilingan.",
                'first_name': first_name, 'username': username, 'email': email
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'accounts/register.html', {
                'error': "Ushbu email bilan avval ro‘yxatdan o‘tilgan.",
                'first_name': first_name, 'username': username, 'email': email
            })

        code = generate_otp_code()
        expires_at = timezone.now() + timedelta(minutes=5)
        password_hash = make_password(password)

        EmailVerification.objects.filter(email=email, is_verified=False).delete()
        EmailVerification.objects.create(
            email=email,
            code=code,
            first_name=first_name,
            username=username,
            password_hash=password_hash,
            expires_at=expires_at
        )

        try:
            send_verification_email(email, code, first_name)
        except Exception:
            pass

        request.session['pending_verification_email'] = email
        request.session['last_otp_sent_at'] = datetime.now().timestamp()
        return redirect('verify_email')

    return render(request, 'accounts/register.html')


def mask_email(email):
    if not email or '@' not in email:
        return email
    parts = email.split('@')
    name = parts[0]
    domain = parts[1]
    if len(name) <= 2:
        masked_name = name[0] + '*'
    else:
        masked_name = name[0] + '*' * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def get_verification_timers(request, verification):
    now = timezone.now()
    remaining_expiry = max(0, int((verification.expires_at - now).total_seconds()))
    last_sent = request.session.get('last_otp_sent_at')
    now_ts = datetime.now().timestamp()
    if last_sent:
        elapsed = int(now_ts - last_sent)
        remaining_resend = max(0, 60 - elapsed)
    else:
        remaining_resend = 0
    return remaining_expiry, remaining_resend


def verify_email_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    email = request.session.get('pending_verification_email')
    if not email:
        return redirect('register')

    verification = EmailVerification.objects.filter(email=email, is_verified=False).first()
    if not verification:
        messages.error(request, "Tasdiqlash ma’lumotlari topilmadi. Iltimos, qaytadan ro‘yxatdan o‘ting.")
        return redirect('register')

    masked = mask_email(email)
    remaining_expiry, remaining_resend = get_verification_timers(request, verification)

    if request.method == 'POST':
        input_code = request.POST.get('code', '').strip()

        if verification.is_expired():
            return render(request, 'accounts/verify_email.html', {
                'error': "Tasdiqlash kodi muddati tugagan. Iltimos, yangi kod so‘rang.",
                'masked_email': masked,
                'remaining_expiry_seconds': 0,
                'remaining_resend_seconds': 0
            })

        if verification.attempts >= 5:
            return render(request, 'accounts/verify_email.html', {
                'error': "Noto‘g‘ri urinishlar soni 5 tadan oshdi. Xavfsizlik yuzasidan yangi kod so‘rashingiz kerak.",
                'masked_email': masked,
                'remaining_expiry_seconds': remaining_expiry,
                'remaining_resend_seconds': remaining_resend
            })

        if input_code != verification.code:
            verification.attempts += 1
            verification.save(update_fields=['attempts'])
            remaining = 5 - verification.attempts
            return render(request, 'accounts/verify_email.html', {
                'error': f"Tasdiqlash kodi noto‘g‘ri. (Qolgan urinishlar: {remaining} ta)",
                'masked_email': masked,
                'remaining_expiry_seconds': remaining_expiry,
                'remaining_resend_seconds': remaining_resend
            })

        if User.objects.filter(username=verification.username).exists():
            return render(request, 'accounts/verify_email.html', {
                'error': "Ushbu foydalanuvchi nomi boshqa birov tomonidan band qilindi. Iltimos, qaytadan ro‘yxatdan o‘ting.",
                'masked_email': masked,
                'remaining_expiry_seconds': remaining_expiry,
                'remaining_resend_seconds': remaining_resend
            })

        if User.objects.filter(email=verification.email).exists():
            return render(request, 'accounts/verify_email.html', {
                'error': "Ushbu email bilan allaqachon hisob yaratilgan.",
                'masked_email': masked,
                'remaining_expiry_seconds': remaining_expiry,
                'remaining_resend_seconds': remaining_resend
            })

        user = User.objects.create(
            username=verification.username,
            email=verification.email,
            first_name=verification.first_name,
            password=verification.password_hash
        )

        verification.is_verified = True
        verification.save(update_fields=['is_verified'])

        request.session.pop('pending_verification_email', None)
        request.session.pop('last_otp_sent_at', None)
        login(request, user)
        messages.success(request, f"🎉 Tabriklaymiz, {user.first_name or user.username}! Pochtani muvaffaqiyatli tasdiqladingiz.")
        return redirect('home')

    return render(request, 'accounts/verify_email.html', {
        'masked_email': masked,
        'remaining_expiry_seconds': remaining_expiry,
        'remaining_resend_seconds': remaining_resend
    })


def resend_verification_code_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method != 'POST':
        return redirect('verify_email')

    email = request.session.get('pending_verification_email')
    if not email:
        return redirect('register')

    verification = EmailVerification.objects.filter(email=email, is_verified=False).first()
    if not verification:
        return redirect('register')

    last_sent = request.session.get('last_otp_sent_at')
    now_ts = datetime.now().timestamp()

    if last_sent and (now_ts - last_sent < 60):
        messages.warning(request, "Iltimos, yangi kod so‘rashdan oldin 60 soniya kuting.")
        return redirect('verify_email')

    new_code = generate_otp_code()
    verification.code = new_code
    verification.expires_at = timezone.now() + timedelta(minutes=5)
    verification.attempts = 0
    verification.save(update_fields=['code', 'expires_at', 'attempts'])

    try:
        send_verification_email(email, new_code, verification.first_name)
    except Exception:
        pass

    request.session['last_otp_sent_at'] = now_ts
    messages.success(request, "Yangi 6 xonali tasdiqlash kodi pochtangizga jo‘natildi.")
    return redirect('verify_email')


def logout_view(request):
    logout(request)
    messages.info(request, "Tizimdan muvaffaqiyatli chiqdingiz.")
    return redirect('home')


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    purchased_items = OrderItem.objects.filter(order__user=request.user, order__status='paid').select_related('product', 'seller', 'order')
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product', 'product__seller', 'product__category')
    user_reviews = Review.objects.filter(user=request.user).select_related('product')

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'purchased_items': purchased_items,
        'wishlist_items': wishlist_items,
        'user_reviews': user_reviews,
    })


@login_required
def settings_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'profile_info':
            new_username = request.POST.get('username', '').strip().lower()
            request.user.first_name = request.POST.get('first_name', '').strip()
            request.user.last_name = request.POST.get('last_name', '').strip()
            new_email = request.POST.get('email', '').strip().lower()

            if new_username and new_username != request.user.username:
                if not re.match(r'^[a-zA-Z0-9_]{3,30}$', new_username):
                    messages.error(request, "Foydalanuvchi nomi 3 dan 30 tagacha lotin harflari, raqamlar va pastki chiziqdan iborat bo‘lishi kerak.")
                    return redirect('settings')
                if User.objects.filter(username=new_username).exclude(pk=request.user.pk).exists():
                    messages.error(request, "Ushbu foydalanuvchi nomi allaqachon band qilingan.")
                    return redirect('settings')
                request.user.username = new_username

            if new_email and new_email != request.user.email:
                if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                    messages.error(request, "Ushbu email boshqa hisob tomonidan band qilingan.")
                    return redirect('settings')
                request.user.email = new_email

            request.user.save()

            profile.phone = request.POST.get('phone', '').strip()
            profile.bio = request.POST.get('bio', '').strip()
            if 'avatar' in request.FILES:
                valid, msg = validate_image_file(request.FILES['avatar'])
                if not valid:
                    messages.error(request, msg)
                    return redirect('settings')
                profile.avatar = request.FILES['avatar']
            profile.save()

            messages.success(request, "Ma’lumotlar muvaffaqiyatli saqlandi.")
            return redirect('settings')

        elif form_type == 'change_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            new_password_confirm = request.POST.get('new_password_confirm', '')

            if not request.user.check_password(current_password):
                messages.error(request, "Hozirgi parol noto‘g‘ri kiritildi.")
            elif new_password != new_password_confirm:
                messages.error(request, "Yangi parollar bir-biriga mos kelmadi.")
            elif len(new_password) < 8:
                messages.error(request, "Yangi parol kamida 8 ta belgidan iborat bo‘lishi kerak.")
            elif not any(char.isdigit() for char in new_password) or not any(char.isalpha() for char in new_password):
                messages.error(request, "Yangi parolda kamida bitta harf va bitta raqam bo‘lishi kerak.")
            else:
                try:
                    validate_password(new_password, request.user)
                    request.user.set_password(new_password)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Parolingiz muvaffaqiyatli yangilandi.")
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))
            return redirect('settings')

    return render(request, 'accounts/settings.html', {'profile': profile})


@login_required
def become_seller_view(request):
    if hasattr(request.user, 'seller_profile'):
        return redirect('dashboard_overview')

    application = SellerApplication.objects.filter(user=request.user, status='pending').first()

    if request.method == 'POST':
        store_name = request.POST.get('store_name', '').strip()
        bio = request.POST.get('bio', '').strip()
        experience = request.POST.get('experience', '').strip()
        portfolio_url = request.POST.get('portfolio_url', '').strip()
        telegram = request.POST.get('telegram', '').strip()

        if not store_name or not bio:
            messages.error(request, "Do‘kon nomi va qisqacha tavsifni kiritish majburiy.")
            return redirect('become_seller')

        if 'avatar' in request.FILES:
            valid, msg = validate_image_file(request.FILES['avatar'])
            if not valid:
                messages.error(request, msg)
                return redirect('become_seller')

        SellerApplication.objects.create(
            user=request.user,
            experience=experience,
            portfolio_url=portfolio_url,
            motivation=f"Store: {store_name} | Telegram: {telegram} | Bio: {bio}",
            status='approved'
        )

        seller = SellerProfile.objects.create(
            user=request.user,
            store_name=store_name,
            bio=bio,
            telegram=telegram,
            is_verified=True
        )

        if 'avatar' in request.FILES:
            seller.avatar = request.FILES['avatar']
            seller.save()

        messages.success(request, "Tabriklaymiz! Siz Codora'da sotuvchi bo‘ldingiz.")
        return redirect('dashboard_overview')

    return render(request, 'accounts/become_seller.html', {
        'already_applied': bool(application)
    })
