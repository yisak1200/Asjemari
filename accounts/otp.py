import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import F
from django.utils import timezone
from django.utils.html import escape

from .email_service import send_email
from .models import EmailOTPChallenge


class OTPError(Exception):
    pass


class OTPRateLimited(OTPError):
    pass


def generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_email_otp(email, purpose):
    now = timezone.now()
    resend_after = now - timedelta(seconds=settings.EMAIL_OTP_RESEND_SECONDS)
    if EmailOTPChallenge.objects.filter(email=email, purpose=purpose, created_at__gte=resend_after).exists():
        raise OTPRateLimited(f"Wait {settings.EMAIL_OTP_RESEND_SECONDS} seconds before requesting another code.")

    hourly_count = EmailOTPChallenge.objects.filter(
        email=email,
        purpose=purpose,
        created_at__gte=now - timedelta(hours=1),
    ).count()
    if hourly_count >= 5:
        raise OTPRateLimited("Too many codes were requested. Try again later.")

    code = generate_otp_code()
    challenge = EmailOTPChallenge.objects.create(
        email=email,
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=settings.EMAIL_OTP_TTL_MINUTES),
    )
    purpose_label = "verify your Asjemari account" if purpose == "signup" else "reset your Asjemari password"
    safe_code = escape(code)
    try:
        send_email(
            to=email,
            subject=f"Your Asjemari verification code is {code}",
            text=f"Use {code} to {purpose_label}. It expires in {settings.EMAIL_OTP_TTL_MINUTES} minutes. If you did not request this, ignore this email.",
            html=(
                '<div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#10251f">'
                '<h1 style="font-size:24px">Asjemari verification</h1>'
                f'<p>Use this code to {escape(purpose_label)}:</p>'
                f'<p style="font-size:32px;font-weight:700;letter-spacing:8px">{safe_code}</p>'
                f'<p>This code expires in {settings.EMAIL_OTP_TTL_MINUTES} minutes.</p>'
                '<p style="color:#64736d">If you did not request this, you can safely ignore this email.</p>'
                '</div>'
            ),
            idempotency_key=f"otp-{purpose}-{challenge.id}",
        )
    except Exception:
        challenge.delete()
        raise

    EmailOTPChallenge.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False,
    ).exclude(id=challenge.id).update(is_used=True)
    return challenge


def consume_email_otp(email, purpose, code):
    challenge = EmailOTPChallenge.objects.filter(
        email=email,
        purpose=purpose,
        is_used=False,
    ).order_by("-created_at").first()
    if not challenge:
        raise OTPError("Request a new verification code.")
    if challenge.expires_at <= timezone.now():
        challenge.is_used = True
        challenge.save(update_fields=["is_used"])
        raise OTPError("This verification code has expired. Request a new one.")
    if challenge.attempts >= 5:
        challenge.is_used = True
        challenge.save(update_fields=["is_used"])
        raise OTPError("Too many incorrect attempts. Request a new code.")
    if not check_password(str(code or ""), challenge.code_hash):
        EmailOTPChallenge.objects.filter(id=challenge.id).update(attempts=F("attempts") + 1)
        raise OTPError("The verification code is incorrect.")
    challenge.is_used = True
    challenge.save(update_fields=["is_used"])
    return challenge
