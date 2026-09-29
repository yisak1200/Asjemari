import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class ResendError(Exception):
    pass


def resend_is_configured():
    key = str(settings.RESEND_API or "").strip()
    return bool(key and not key.startswith("re_your-") and "replace" not in key.lower())


def send_email(*, to, subject, html, text, idempotency_key=None):
    if not resend_is_configured():
        raise ResendError("Email delivery is not configured.")

    payload = json.dumps({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API}",
        "Content-Type": "application/json",
        "User-Agent": "Asjemari/1.0",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key[:256]

    request = Request(
        f"{settings.RESEND_API_BASE_URL}/emails",
        data=payload,
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            result = json.loads(error.read().decode("utf-8"))
            message = result.get("message") or result.get("error")
        except (ValueError, AttributeError):
            message = None
        raise ResendError(message or "The email provider rejected the message.") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise ResendError("The email provider could not be reached.") from error

    if not result.get("id"):
        raise ResendError("The email provider did not accept the message.")
    return result
