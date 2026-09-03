import re
import uuid
import mimetypes
from pathlib import Path
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import FileResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from startup_company.models import StartupCompany
from .chapa import ChapaError, initialize_transaction, reconcile_transaction
from .models import Campaign, CampaignCategory, CampaignLike, CampaignMedia, Donation, FundTransaction, ReportCampaign, WithdrawalRequest


def funded_donations(campaign):
    return campaign.donation_set.filter(
        Q(fundtransaction__isnull=True) |
        Q(fundtransaction__is_paid=True, fundtransaction__payment_status="Approved")
    )


def contribution_payload(contribution):
    anonymous = contribution.is_anonymous
    account_name = contribution.donor.full_name if contribution.donor else ""
    return {
        "id": str(contribution.id),
        "name": "Anonymous supporter" if anonymous else contribution.name or account_name or "Supporter",
        "amount": str(contribution.amount),
        "comment": contribution.comment or "",
        "created_at": contribution.created_at,
        "anonymous": anonymous,
    }


def withdrawal_payload(item):
    return {
        "id": str(item.id),
        "campaign_id": str(item.campaign_id),
        "campaign_title": item.campaign.campaign_title,
        "bank_name": item.bank_name,
        "bank_label": item.get_bank_name_display(),
        "account_number": item.account_number,
        "amount": str(item.amount),
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def campaign_available_to_withdraw(campaign):
    raised = funded_donations(campaign).aggregate(total=Sum("amount"))["total"] or 0
    completed = campaign.withdrawal_requests.filter(status="Completed").aggregate(total=Sum("amount"))["total"] or 0
    return max(raised - completed, 0)


def campaign_payload(campaign, request=None):
    donations = funded_donations(campaign)
    raised = donations.aggregate(total=Sum("amount"))["total"] or 0
    cover_image = campaign.cover_image.url if campaign.cover_image else ""
    if cover_image and request:
        cover_image = request.build_absolute_uri(cover_image)
    liked_by_me = False
    if request and request.user.is_authenticated:
        liked_by_me = campaign.likes.filter(user=request.user).exists()
    return {
        "id": str(campaign.id),
        "title": campaign.campaign_title,
        "description": campaign.campaign_description,
        "category": campaign.category.name,
        "location": campaign.location or "Ethiopia",
        "target_amount": str(campaign.target_amount),
        "raised_amount": str(raised),
        "contribution_count": donations.count(),
        "status": campaign.campaign_status,
        "creator_name": campaign.campaign_creator.full_name or campaign.campaign_creator.email,
        "created_at": campaign.created_at,
        "demo_media_count": campaign.demo_media.count(),
        "cover_image": cover_image,
        "like_count": campaign.likes.count(),
        "liked_by_me": liked_by_me,
    }


class CampaignListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        campaigns = Campaign.objects.filter(campaign_status__iexact="Approved").select_related("category", "campaign_creator").prefetch_related("likes").order_by("-created_at")
        categories = CampaignCategory.objects.annotate(
            campaign_count=Count(
                "campaign",
                filter=Q(campaign__campaign_status__iexact="Approved"),
            )
        ).order_by("name")
        funded_filter = Q(donation__fundtransaction__isnull=True) | Q(
            donation__fundtransaction__is_paid=True,
            donation__fundtransaction__payment_status="Approved",
        )
        totals = campaigns.aggregate(
            total_raised=Sum("donation__amount", filter=funded_filter),
            total_supporters=Count("donation", filter=funded_filter, distinct=True),
        )
        return Response({
            "campaigns": [campaign_payload(campaign, request) for campaign in campaigns],
            "categories": [{
                "id": str(category.id),
                "name": category.name,
                "description": category.description,
                "campaign_count": category.campaign_count,
            } for category in categories],
            "stats": {
                "campaign_count": campaigns.count(),
                "verified_creators": campaigns.values("campaign_creator_id").distinct().count(),
                "total_raised": str(totals["total_raised"] or 0),
                "total_supporters": totals["total_supporters"] or 0,
                "locations_reached": campaigns.exclude(location__isnull=True).exclude(location="").values("location").distinct().count(),
            },
        })


class CampaignDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, campaign_id):
        campaign = (
            Campaign.objects.filter(id=campaign_id, campaign_status__iexact="Approved")
            .select_related("category", "campaign_creator", "startup_company")
            .prefetch_related("demo_media", "likes")
            .first()
        )
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = campaign_payload(campaign, request)
        payload["demo_media"] = [
            {
                "id": str(media.id),
                "type": media.media_type,
                "url": request.build_absolute_uri(media.file.url),
            }
            for media in campaign.demo_media.all()
            if media.file and media.file.storage.exists(media.file.name)
        ]

        startup = campaign.startup_company
        payload["startup"] = None
        payload["pitch_deck"] = None
        if startup:
            payload["startup"] = {
                "name": startup.company_name,
                "description": startup.company_description,
                "traction": startup.Traction_describtion,
                "website": startup.company_website or "",
            }
            if startup.pitch_deck and startup.pitch_deck.storage.exists(startup.pitch_deck.name):
                payload["pitch_deck"] = {
                    "name": Path(startup.pitch_deck.name).name,
                    "url": request.build_absolute_uri(reverse("campaign_pitch_deck", args=[campaign.id])),
                }

        contributions = funded_donations(campaign).select_related("donor").order_by("-created_at")[:6]
        payload["recent_contributions"] = [contribution_payload(item) for item in contributions]
        return Response(payload)


@method_decorator(xframe_options_exempt, name="dispatch")
class CampaignPitchDeckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, campaign_id):
        campaign = Campaign.objects.filter(
            id=campaign_id,
            campaign_status__iexact="Approved",
        ).select_related("startup_company").first()
        if not campaign or not campaign.startup_company or not campaign.startup_company.pitch_deck:
            return Response({"error": "Pitch deck not found."}, status=status.HTTP_404_NOT_FOUND)
        deck = campaign.startup_company.pitch_deck
        if not deck.storage.exists(deck.name):
            return Response({"error": "Pitch deck not found."}, status=status.HTTP_404_NOT_FOUND)
        content_type = mimetypes.guess_type(deck.name)[0] or "application/octet-stream"
        return FileResponse(deck.open("rb"), content_type=content_type, filename=Path(deck.name).name)


class CampaignCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        startup_id = request.data.get("startup_id")
        startups = StartupCompany.objects.filter(user=request.user, company_status="Approved")
        startup = startups.filter(id=startup_id).first() if startup_id else startups.first()
        if not startup or startup.company_status != "Approved":
            return Response({"error": "Select an approved startup before creating a campaign."}, status=status.HTTP_403_FORBIDDEN)

        required = ["title", "description", "category", "target_amount"]
        if any(not request.data.get(field) for field in required) or not request.FILES.get("cover_image"):
            return Response({"error": "Title, description, category, target amount and cover image are required."}, status=status.HTTP_400_BAD_REQUEST)

        category_name = request.data["category"].strip()
        category = CampaignCategory.objects.filter(name__iexact=category_name).first()
        if not category:
            return Response({"error": "Select a valid campaign category."}, status=status.HTTP_400_BAD_REQUEST)
        campaign = Campaign.objects.create(
            category=category,
            campaign_creator=request.user,
            campaign_title=request.data["title"],
            campaign_description=request.data["description"],
            cover_image=request.FILES["cover_image"],
            startup_company=startup,
            creator_type="Startup",
            target_amount=request.data["target_amount"],
            location=request.data.get("location") or startup.location,
            campaign_status="Pending",
        )
        for media_file in request.FILES.getlist("demo_media"):
            media_type = "video" if (media_file.content_type or "").startswith("video/") else "image"
            CampaignMedia.objects.create(campaign=campaign, file=media_file, media_type=media_type)
        return Response({"message": "Campaign submitted for review.", "campaign_id": str(campaign.id), "status": campaign.campaign_status}, status=status.HTTP_201_CREATED)


class CampaignLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, campaign_id):
        campaign = Campaign.objects.filter(id=campaign_id, campaign_status__iexact="Approved").first()
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        like, created = CampaignLike.objects.get_or_create(campaign=campaign, user=request.user)
        if not created:
            like.delete()
        return Response({"liked": created, "like_count": campaign.likes.count()})


class MyCampaignListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        campaigns = Campaign.objects.filter(campaign_creator=request.user).select_related("category").order_by("-created_at")
        return Response({"campaigns": [campaign_payload(campaign, request) for campaign in campaigns]})


class CampaignManageView(APIView):
    permission_classes = [IsAuthenticated]

    def get_campaign(self, request, campaign_id):
        return Campaign.objects.filter(id=campaign_id, campaign_creator=request.user).select_related("category").first()

    def get(self, request, campaign_id):
        campaign = self.get_campaign(request, campaign_id)
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(campaign_payload(campaign, request))

    def patch(self, request, campaign_id):
        campaign = self.get_campaign(request, campaign_id)
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        if campaign.campaign_status in ["Completed", "suspended"]:
            return Response({"error": "This campaign can no longer be edited."}, status=status.HTTP_400_BAD_REQUEST)

        if request.data.get("title"):
            campaign.campaign_title = request.data["title"].strip()
        if request.data.get("description"):
            campaign.campaign_description = request.data["description"].strip()
        if request.data.get("location"):
            campaign.location = request.data["location"].strip()
        if request.data.get("target_amount"):
            campaign.target_amount = request.data["target_amount"]
        if request.data.get("category"):
            category_name = request.data["category"].strip()
            category = CampaignCategory.objects.filter(name__iexact=category_name).first()
            if not category:
                return Response({"error": "Select a valid campaign category."}, status=status.HTTP_400_BAD_REQUEST)
            campaign.category = category
        if request.FILES.get("cover_image"):
            campaign.cover_image = request.FILES["cover_image"]
        campaign.save()
        return Response({"message": "Campaign updated.", "campaign": campaign_payload(campaign, request)})

    def delete(self, request, campaign_id):
        campaign = self.get_campaign(request, campaign_id)
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        raised = funded_donations(campaign).aggregate(total=Sum("amount"))["total"] or 0
        if raised != 0:
            return Response({"error": "Campaigns with funded money cannot be deleted."}, status=status.HTTP_400_BAD_REQUEST)
        campaign.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CampaignReportView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, campaign_id):
        campaign = Campaign.objects.filter(id=campaign_id, campaign_status__iexact="Approved").first()
        reason = (request.data.get("reason") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        if not reason:
            return Response({"error": "Tell us why you are reporting this campaign."}, status=status.HTTP_400_BAD_REQUEST)
        report = ReportCampaign.objects.create(
            campaign=campaign,
            reporter=request.user if request.user.is_authenticated else None,
            name=name or (request.user.full_name if request.user.is_authenticated else "Anonymous reporter"),
            reason=reason,
        )
        return Response({"message": "Report submitted. Our team will review it.", "report_id": str(report.id)}, status=status.HTTP_201_CREATED)


class CampaignContributionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, campaign_id):
        campaign = Campaign.objects.filter(id=campaign_id, campaign_creator=request.user).first()
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        contributions = funded_donations(campaign).select_related("donor").order_by("-created_at")
        return Response({
            "campaign_id": str(campaign.id),
            "contributions": [contribution_payload(item) for item in contributions],
        })


class WithdrawalRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        campaigns = Campaign.objects.filter(
            campaign_creator=request.user,
            campaign_status__iexact="Approved",
        ).select_related("category").order_by("-created_at")
        withdrawals = WithdrawalRequest.objects.filter(requester=request.user).select_related("campaign").order_by("-created_at")
        return Response({
            "banks": [{"value": value, "label": label} for value, label in WithdrawalRequest.BANK_CHOICES],
            "campaigns": [{
                "id": str(campaign.id),
                "title": campaign.campaign_title,
                "available_amount": str(campaign_available_to_withdraw(campaign)),
                "has_active_request": campaign.withdrawal_requests.filter(status__in=["Pending", "Processing"]).exists(),
            } for campaign in campaigns],
            "withdrawals": [withdrawal_payload(item) for item in withdrawals],
        })

    @transaction.atomic
    def post(self, request):
        campaign = Campaign.objects.select_for_update().filter(
            id=request.data.get("campaign_id"),
            campaign_creator=request.user,
            campaign_status__iexact="Approved",
        ).first()
        if not campaign:
            return Response({"error": "Select one of your approved campaigns."}, status=status.HTTP_404_NOT_FOUND)
        if campaign.withdrawal_requests.filter(status__in=["Pending", "Processing"]).exists():
            return Response({"error": "This campaign already has an active withdrawal request."}, status=status.HTTP_400_BAD_REQUEST)
        bank_name = request.data.get("bank_name")
        if bank_name not in dict(WithdrawalRequest.BANK_CHOICES):
            return Response({"error": "Select a supported bank."}, status=status.HTTP_400_BAD_REQUEST)
        account_number = re.sub(r"\s+", "", str(request.data.get("account_number") or ""))
        if not re.fullmatch(r"\d{8,24}", account_number):
            return Response({"error": "Enter a valid bank account number using 8 to 24 digits."}, status=status.HTTP_400_BAD_REQUEST)
        amount = campaign_available_to_withdraw(campaign)
        if amount <= 0:
            return Response({"error": "This campaign has no available funded balance to withdraw."}, status=status.HTTP_400_BAD_REQUEST)
        item = WithdrawalRequest.objects.create(
            campaign=campaign,
            requester=request.user,
            bank_name=bank_name,
            account_number=account_number,
            amount=amount,
        )
        return Response({"message": "Withdrawal request submitted.", "withdrawal": withdrawal_payload(item)}, status=status.HTTP_201_CREATED)


class ChapaPaymentInitializeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, campaign_id):
        campaign = Campaign.objects.filter(id=campaign_id, campaign_status__iexact="Approved").first()
        if not campaign:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)

        currency = str(request.data.get("currency") or "ETB").upper()
        if currency not in {"ETB", "USD"}:
            return Response({"error": "Choose ETB or USD."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            contribution_amount = Decimal(str(request.data.get("amount") or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError):
            contribution_amount = Decimal("0")
        if not contribution_amount.is_finite():
            contribution_amount = Decimal("0")
        minimum_amount = Decimal("10") if currency == "ETB" else Decimal("1")
        if contribution_amount < minimum_amount:
            return Response({"error": f"The minimum contribution is {minimum_amount:g} {currency}."}, status=status.HTTP_400_BAD_REQUEST)
        if currency == "USD" and contribution_amount > Decimal("10000"):
            return Response({"error": "The maximum USD contribution is 10,000 USD."}, status=status.HTTP_400_BAD_REQUEST)
        exchange_rate = Decimal("1") if currency == "ETB" else Decimal("0")
        fee_amount = (contribution_amount * settings.CHAPA_FEE_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        charged_amount = contribution_amount + fee_amount
        campaign_amount = contribution_amount if currency == "ETB" else Decimal("0")

        anonymous = bool(request.data.get("anonymous"))
        name = (request.data.get("name") or "").strip()
        email = (request.data.get("email") or "").strip()
        phone_number = re.sub(r"[^0-9+]", "", request.data.get("phone_number") or "")
        if phone_number.startswith("+251"):
            phone_number = "0" + phone_number[4:]
        if phone_number and not re.fullmatch(r"0[79]\d{8}", phone_number):
            return Response({"error": "Use a valid Ethiopian mobile number such as 0911234567."}, status=status.HTTP_400_BAD_REQUEST)
        if email:
            try:
                validate_email(email)
            except ValidationError:
                return Response({"error": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated:
            email = email or request.user.email
            name = name or request.user.full_name
        public_name = "" if anonymous else name
        tx_ref = f"asj-{uuid.uuid4().hex}"
        donation = Donation.objects.create(
            campaign=campaign,
            donor=request.user if request.user.is_authenticated and not anonymous else None,
            name=public_name,
            is_anonymous=anonymous,
            amount=campaign_amount,
            comment=(request.data.get("comment") or "").strip(),
        )
        FundTransaction.objects.create(
            donation=donation,
            payment_gateway="Chapa",
            transaction_id=tx_ref,
            balance=0,
            payment_status="Pending",
            currency=currency,
            contribution_amount=contribution_amount,
            transaction_fee=fee_amount,
            charged_amount=charged_amount,
            exchange_rate=exchange_rate,
        )

        full_name = name or "Asjemari Supporter"
        first_name, _, last_name = full_name.partition(" ")
        callback_url = settings.CHAPA_CALLBACK_URL or request.build_absolute_uri(reverse("chapa_payment_callback"))
        return_url = f"{settings.CHAPA_WEB_APP_URL}/payment/return?tx_ref={quote(tx_ref)}"
        payload = {
            "amount": str(charged_amount),
            "currency": currency,
            "first_name": first_name,
            "last_name": last_name or "Supporter",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "return_url": return_url,
            "customization": {
                "title": "Asjemari",
                "description": campaign.campaign_title[:100],
            },
            "meta": {
                "campaign_id": str(campaign.id),
                "payment_reason": f"Contribution to {campaign.campaign_title[:120]}",
                "contribution_amount": str(contribution_amount),
                "processing_fee": str(fee_amount),
                "campaign_credit_etb": str(campaign_amount),
            },
        }
        if email:
            payload["email"] = email
        if phone_number:
            payload["phone_number"] = phone_number
        try:
            checkout_url = initialize_transaction(payload)
        except ChapaError as error:
            donation.delete()
            return Response({"error": str(error)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({
            "checkout_url": checkout_url,
            "tx_ref": tx_ref,
            "status": "Pending",
            "currency": currency,
            "contribution_amount": str(contribution_amount),
            "fee_amount": str(fee_amount),
            "charged_amount": str(charged_amount),
            "campaign_credit_etb": str(campaign_amount),
        }, status=status.HTTP_201_CREATED)


class ChapaPaymentOptionsView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "fee_rate": str(settings.CHAPA_FEE_RATE),
            "currencies": [
                {"code": "ETB", "minimum": "10", "maximum": None, "etb_rate": "1", "enabled": True},
                {"code": "USD", "minimum": "1", "maximum": "10000", "etb_rate": None, "enabled": True},
            ],
        })


class ChapaPaymentCallbackView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        tx_ref = (
            request.query_params.get("tx_ref") or
            request.query_params.get("trx_ref") or
            request.data.get("tx_ref") or
            request.data.get("trx_ref")
        )
        if not tx_ref:
            return Response({"error": "Payment reference is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            fund_transaction = reconcile_transaction(tx_ref)
        except ChapaError as error:
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"tx_ref": tx_ref, "status": fund_transaction.payment_status, "paid": fund_transaction.is_paid})


class ChapaPaymentStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, tx_ref):
        fund_transaction = FundTransaction.objects.select_related("donation__campaign").filter(transaction_id=tx_ref).first()
        if not fund_transaction:
            return Response({"error": "Payment reference not found."}, status=status.HTTP_404_NOT_FOUND)
        if fund_transaction.payment_status == "Pending":
            try:
                fund_transaction = reconcile_transaction(tx_ref)
            except ChapaError:
                fund_transaction.refresh_from_db()
        campaign = fund_transaction.donation.campaign
        return Response({
            "tx_ref": tx_ref,
            "status": fund_transaction.payment_status,
            "paid": fund_transaction.is_paid,
            "amount": str(fund_transaction.contribution_amount or fund_transaction.donation.amount),
            "currency": fund_transaction.currency or "ETB",
            "fee_amount": str(fund_transaction.transaction_fee),
            "charged_amount": str(fund_transaction.charged_amount or fund_transaction.donation.amount),
            "campaign_credit_etb": str(fund_transaction.donation.amount),
            "exchange_rate": str(fund_transaction.exchange_rate),
            "swap_status": fund_transaction.swap_status,
            "campaign": campaign_payload(campaign, request),
        })
