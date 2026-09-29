from django.utils.html import escape

from .email_service import ResendError, send_email


def send_startup_approved_email(startup):
    recipient = startup.user.email
    company_name = startup.company_name
    try:
        send_email(
            to=recipient,
            subject=f"{company_name} is approved on Asjemari",
            text=f"Good news: {company_name} has been approved. You can now continue creating and managing campaigns on Asjemari.",
            html=(
                '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#10251f">'
                '<h1 style="font-size:24px">Your startup is approved</h1>'
                f'<p>Good news—<strong>{escape(company_name)}</strong> has been approved.</p>'
                '<p>You can now continue creating and managing campaigns on Asjemari.</p>'
                '</div>'
            ),
            idempotency_key=f"startup-approved-{startup.id}",
        )
    except ResendError:
        return False
    return True


def send_campaign_approved_email(campaign):
    recipient = campaign.campaign_creator.email
    campaign_title = campaign.campaign_title
    try:
        send_email(
            to=recipient,
            subject=f"{campaign_title} is approved on Asjemari",
            text=f"Good news: {campaign_title} has been approved and is now ready to receive community support on Asjemari.",
            html=(
                '<div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#10251f">'
                '<h1 style="font-size:24px">Your campaign is approved</h1>'
                f'<p>Good news—<strong>{escape(campaign_title)}</strong> has been approved.</p>'
                '<p>Your campaign is now ready to receive community support on Asjemari.</p>'
                '</div>'
            ),
            idempotency_key=f"campaign-approved-{campaign.id}",
        )
    except ResendError:
        return False
    return True
