import random
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


from email.utils import formataddr


def get_safe_from_email():
    raw = getattr(settings, 'DEFAULT_FROM_EMAIL', '') or 'Codora <noreply@codora.uz>'
    if '<' in raw and '>' in raw:
        name = raw.split('<')[0].strip(' "\'')
        addr = raw.split('<')[1].replace('>', '').strip(' "\'')
        return formataddr((name, addr))
    return raw


def generate_otp_code():
    return str(random.randint(100000, 999999))


def send_verification_email(email, code, first_name=""):
    subject = f"{code} — Codora platformasida ro‘yxatdan o‘tish kodi"
    context = {
        'code': code,
        'first_name': first_name,
        'email': email,
    }
    html_message = render_to_string('emails/verification_code.html', context)
    plain_message = strip_tags(html_message)
    from_email = get_safe_from_email()

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=from_email,
        recipient_list=[email],
        html_message=html_message,
        fail_silently=False
    )
