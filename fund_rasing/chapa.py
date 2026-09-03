import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import FundTransaction


class ChapaError(Exception):
    pass


def _request(method, path, payload=None):
    if not settings.CHAPA_SECRET_KEY:
        raise ChapaError("Chapa is not configured on the server.")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{settings.CHAPA_API_BASE_URL}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {settings.CHAPA_SECRET_KEY}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        try:
            result = json.loads(error.read().decode("utf-8"))
            message = result.get("message") or result.get("error")
        except (ValueError, AttributeError):
            message = None
        raise ChapaError(message or "Chapa rejected the payment request.") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise ChapaError("Chapa could not be reached. Please try again.") from error
    if result.get("status") != "success":
        raise ChapaError(result.get("message") or "Chapa could not process the payment request.")
    return result


def initialize_transaction(payload):
    result = _request("POST", "/transaction/initialize", payload)
    checkout_url = (result.get("data") or {}).get("checkout_url")
    if not checkout_url:
        raise ChapaError("Chapa did not return a checkout link.")
    return checkout_url


def verify_transaction(tx_ref):
    return _request("GET", f"/transaction/verify/{quote(tx_ref, safe='')}")


def swap_usd_to_etb(amount):
    return _request("POST", "/swap", {"amount": str(amount), "from": "USD", "to": "ETB"})


def _positive_decimal(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def extract_swap_amount(result, usd_amount):
    """Read the ETB proceeds while tolerating Chapa response-envelope changes."""
    mappings = []

    def collect(value):
        if isinstance(value, dict):
            mappings.append(value)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(result)
    amount_keys = (
        "converted_amount", "to_amount", "amount_received", "received_amount",
        "etb_amount", "target_amount", "amount_to", "destination_amount",
    )
    for mapping in mappings:
        normalized = {str(key).lower(): value for key, value in mapping.items()}
        for key in amount_keys:
            amount = _positive_decimal(normalized.get(key))
            if amount is not None:
                return amount.quantize(Decimal("0.01"))

    for mapping in mappings:
        normalized = {str(key).lower(): value for key, value in mapping.items()}
        for key in ("exchange_rate", "rate"):
            rate = _positive_decimal(normalized.get(key))
            if rate is not None:
                return (usd_amount * rate).quantize(Decimal("0.01"))

    for mapping in mappings:
        normalized = {str(key).lower(): value for key, value in mapping.items()}
        target_currency = str(normalized.get("to") or normalized.get("currency") or normalized.get("target_currency") or "").upper()
        amount = _positive_decimal(normalized.get("amount"))
        if target_currency == "ETB" and amount is not None and amount > usd_amount:
            return amount.quantize(Decimal("0.01"))
    return None


def reconcile_transaction(tx_ref):
    fund_transaction = FundTransaction.objects.select_related("donation__campaign").filter(transaction_id=tx_ref).first()
    if not fund_transaction:
        raise ChapaError("Payment reference not found.")
    if fund_transaction.is_paid and fund_transaction.payment_status == "Approved":
        return fund_transaction

    result = verify_transaction(tx_ref)
    data = result.get("data") or {}
    chapa_status = str(data.get("status") or "").lower()
    try:
        verified_amount = Decimal(str(data.get("amount")))
    except (InvalidOperation, TypeError):
        verified_amount = Decimal("-1")
    verified_ref = str(data.get("tx_ref") or data.get("trx_ref") or "")
    currency = str(data.get("currency") or "").upper()
    expected_amount = fund_transaction.charged_amount if fund_transaction.charged_amount > 0 else fund_transaction.donation.amount
    expected_currency = (fund_transaction.currency or "ETB").upper()

    payment_verified = chapa_status == "success" and verified_ref == tx_ref and currency == expected_currency and verified_amount == expected_amount
    if payment_verified and expected_currency == "USD":
        with transaction.atomic():
            current = FundTransaction.objects.select_for_update().select_related("donation__campaign").get(pk=fund_transaction.pk)
            if current.payment_status == "Approved" and current.swap_status == "Completed":
                return current
            if current.swap_status in {"Processing", "Review"}:
                return current
            current.is_paid = True
            current.swap_status = "Processing"
            current.swap_attempted_at = timezone.now()
            current.save(update_fields=["is_paid", "swap_status", "swap_attempted_at"])

        try:
            swap_result = swap_usd_to_etb(current.contribution_amount)
        except ChapaError as error:
            current.swap_status = "Review"
            current.swap_response = {"error": str(error)}
            current.save(update_fields=["swap_status", "swap_response"])
            return current

        etb_amount = extract_swap_amount(swap_result, current.contribution_amount)
        if etb_amount is None:
            current.swap_status = "Review"
            current.swap_response = swap_result
            current.save(update_fields=["swap_status", "swap_response"])
            return current

        with transaction.atomic():
            current = FundTransaction.objects.select_for_update().select_related("donation__campaign").get(pk=fund_transaction.pk)
            if current.swap_status != "Processing":
                return current
            current.donation.amount = etb_amount
            current.donation.save(update_fields=["amount"])
            current.exchange_rate = (etb_amount / current.contribution_amount).quantize(Decimal("0.0001"))
            current.swap_amount_etb = etb_amount
            current.swap_response = swap_result
            current.swap_status = "Completed"
            current.is_paid = True
            current.payment_status = "Approved"
            current.balance = etb_amount
            current.save(update_fields=[
                "exchange_rate", "swap_amount_etb", "swap_response", "swap_status",
                "is_paid", "payment_status", "balance",
            ])
            campaign = current.donation.campaign
            paid_total = campaign.donation_set.filter(
                Q(fundtransaction__isnull=True) |
                Q(fundtransaction__is_paid=True, fundtransaction__payment_status="Approved")
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            if paid_total >= campaign.target_amount and not campaign.is_completed:
                campaign.is_completed = True
                campaign.save(update_fields=["is_completed"])
            return current

    if payment_verified:
        with transaction.atomic():
            current = FundTransaction.objects.select_for_update().select_related("donation__campaign").get(pk=fund_transaction.pk)
            current.is_paid = True
            current.payment_status = "Approved"
            current.balance = current.donation.amount
            current.save(update_fields=["is_paid", "payment_status", "balance"])
            campaign = current.donation.campaign
            paid_total = campaign.donation_set.filter(
                Q(fundtransaction__isnull=True) |
                Q(fundtransaction__is_paid=True, fundtransaction__payment_status="Approved")
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            if paid_total >= campaign.target_amount and not campaign.is_completed:
                campaign.is_completed = True
                campaign.save(update_fields=["is_completed"])
            return current

    verification_mismatch = chapa_status == "success" and (
        verified_ref != tx_ref or currency != expected_currency or verified_amount != expected_amount
    )
    terminal_failure = any(value in chapa_status for value in ("failed", "cancelled", "canceled", "reversed"))
    if verification_mismatch or terminal_failure:
        fund_transaction.payment_status = "Rejected"
        fund_transaction.is_paid = False
        fund_transaction.save(update_fields=["payment_status", "is_paid"])
    return fund_transaction
