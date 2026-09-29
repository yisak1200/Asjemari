from django.utils import timezone
from django.utils.html import escape

from accounts.email_service import ResendError, send_email

from .models import FundTransaction


def send_contribution_notification(payment):
    payment = FundTransaction.objects.select_related(
        "donation__donor",
        "donation__campaign",
    ).filter(id=payment.id).first()
    if (
        not payment
        or not payment.is_paid
        or payment.payment_status != "Approved"
        or payment.contribution_notified_at
        or not payment.donation.donor
        or not payment.donation.donor.email
    ):
        return False

    donor = payment.donation.donor
    campaign = payment.donation.campaign
    amount = payment.contribution_amount or payment.donation.amount
    currency = payment.currency or "ETB"
    try:
        send_email(
            to=donor.email,
            subject=f"Contribution confirmed for {campaign.campaign_title}",
            text=f"Your contribution of {amount} {currency} to {campaign.campaign_title} was confirmed. Transaction reference: {payment.transaction_id}.",
            html=(
                '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#10251f">'
                '<h1 style="font-size:24px">Contribution confirmed</h1>'
                f'<p>Thank you, {escape(donor.full_name or "supporter")}.</p>'
                f'<p>Your contribution of <strong>{escape(str(amount))} {escape(currency)}</strong> to '
                f'<strong>{escape(campaign.campaign_title)}</strong> was confirmed.</p>'
                f'<p style="color:#64736d">Reference: {escape(payment.transaction_id)}</p>'
                '</div>'
            ),
            idempotency_key=f"contribution-confirmed-{payment.transaction_id}",
        )
    except ResendError:
        return False

    FundTransaction.objects.filter(
        id=payment.id,
        contribution_notified_at__isnull=True,
    ).update(contribution_notified_at=timezone.now())
    return True
