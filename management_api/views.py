from django.db.models import Q, Sum
from pathlib import Path
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from fund_rasing.models import Campaign, CampaignCategory, WithdrawalRequest
from startup_company.models import StartupCompany


def startup_payload(startup, request=None):
    identity = StartupCompany.objects.filter(user=startup.user).filter(
        Q(fayda_front_image__isnull=False, fayda_back_image__isnull=False)
        | (Q(fayda_number__isnull=False) & ~Q(fayda_number=""))
    ).first()
    front = startup.fayda_front_image or (identity.fayda_front_image if identity else None)
    back = startup.fayda_back_image or (identity.fayda_back_image if identity else None)
    front_url = front.url if front else ""
    back_url = back.url if back else ""
    if request:
        front_url = request.build_absolute_uri(front_url) if front_url else ""
        back_url = request.build_absolute_uri(back_url) if back_url else ""
    pitch_deck_url = ""
    pitch_deck_name = ""
    if startup.pitch_deck and startup.pitch_deck.storage.exists(startup.pitch_deck.name):
        pitch_deck_url = startup.pitch_deck.url
        pitch_deck_name = Path(startup.pitch_deck.name).name
        if request:
            pitch_deck_url = request.build_absolute_uri(pitch_deck_url)
    return {
        "id": str(startup.id),
        "company_name": startup.company_name,
        "company_description": startup.company_description,
        "location": startup.location or "",
        "tin": startup.tin or (startup.kyc.Tin if startup.kyc else ""),
        "company_website": startup.company_website or "",
        "company_email": startup.company_email or startup.user.email,
        "company_phone_number": startup.company_phone_number or "",
        "traction_description": startup.Traction_describtion or "",
        "pitch_deck": pitch_deck_url,
        "pitch_deck_name": pitch_deck_name,
        "fayda_number": startup.fayda_number or (identity.fayda_number if identity else ""),
        "fayda_front_image": front_url,
        "fayda_back_image": back_url,
        "fayda_status": startup.fayda_status,
        "company_status": startup.company_status,
        "user": {"id": str(startup.user.id), "full_name": startup.user.full_name or "", "email": startup.user.email},
    }


def campaign_payload(campaign):
    raised = campaign.donation_set.aggregate(total=Sum("amount"))["total"] or 0
    return {
        "id": str(campaign.id),
        "title": campaign.campaign_title,
        "creator": campaign.campaign_creator.full_name or campaign.campaign_creator.email,
        "company": campaign.startup_company.company_name if campaign.startup_company else "",
        "category": campaign.category.name,
        "location": campaign.location or "",
        "target_amount": str(campaign.target_amount),
        "raised_amount": str(raised),
        "contribution_count": campaign.donation_set.count(),
        "status": campaign.campaign_status,
        "is_active": campaign.is_active,
        "created_at": campaign.created_at,
    }


def withdrawal_payload(item):
    return {
        "id": str(item.id),
        "campaign_id": str(item.campaign_id),
        "campaign_title": item.campaign.campaign_title,
        "creator_name": item.requester.full_name or item.requester.email,
        "creator_email": item.requester.email,
        "bank_name": item.bank_name,
        "bank_label": item.get_bank_name_display(),
        "account_number": item.account_number,
        "amount": str(item.amount),
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


class OverviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_raised = Campaign.objects.aggregate(total=Sum("donation__amount"))["total"] or 0
        return Response({
            "users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "startups_pending": StartupCompany.objects.filter(company_status="Pending").count(),
            "fayda_pending": StartupCompany.objects.filter(fayda_status="Pending").filter(
                Q(fayda_front_image__isnull=False, fayda_back_image__isnull=False)
                | (Q(fayda_number__isnull=False) & ~Q(fayda_number=""))
            ).count(),
            "campaigns": Campaign.objects.count(),
            "campaigns_pending": Campaign.objects.filter(campaign_status="Pending").count(),
            "total_raised": str(total_raised),
        })


class CategoryListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        categories = CampaignCategory.objects.order_by("name")
        return Response({"categories": [{"id": str(item.id), "name": item.name, "description": item.description, "campaign_count": item.campaign_set.count()} for item in categories]})

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        description = (request.data.get("description") or "").strip()
        if not name or not description:
            return Response({"error": "Name and description are required."}, status=status.HTTP_400_BAD_REQUEST)
        if CampaignCategory.objects.filter(name__iexact=name).exists():
            return Response({"error": "This category already exists."}, status=status.HTTP_400_BAD_REQUEST)
        item = CampaignCategory.objects.create(name=name, description=description)
        return Response({"id": str(item.id), "name": item.name, "description": item.description, "campaign_count": 0}, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, category_id):
        item = CampaignCategory.objects.filter(id=category_id).first()
        if not item:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        item.name = (request.data.get("name") or item.name).strip()
        item.description = (request.data.get("description") or item.description).strip()
        item.save()
        return Response({"id": str(item.id), "name": item.name, "description": item.description, "campaign_count": item.campaign_set.count()})

    def delete(self, request, category_id):
        item = CampaignCategory.objects.filter(id=category_id).first()
        if not item:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        if item.campaign_set.exists():
            return Response({"error": "Move or remove campaigns before deleting this category."}, status=status.HTTP_400_BAD_REQUEST)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FaydaReviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, startup_id=None):
        startups = StartupCompany.objects.filter(
            Q(fayda_front_image__isnull=False, fayda_back_image__isnull=False)
            | (Q(fayda_number__isnull=False) & ~Q(fayda_number=""))
        ).select_related("user").order_by("company_name")
        return Response({"reviews": [startup_payload(item, request) for item in startups]})

    def patch(self, request, startup_id):
        startup = StartupCompany.objects.filter(id=startup_id).select_related("user").first()
        decision = request.data.get("status")
        if not startup or decision not in ["Approved", "Rejected"]:
            return Response({"error": "Valid startup and decision are required."}, status=status.HTTP_400_BAD_REQUEST)
        StartupCompany.objects.filter(user=startup.user).update(fayda_status=decision)
        return Response({"message": f"Fayda identity {decision.lower()}.", "review": startup_payload(StartupCompany.objects.get(id=startup.id), request)})


class StartupReviewView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, startup_id=None):
        startups = StartupCompany.objects.select_related("user", "kyc").order_by("company_name")
        return Response({"startups": [startup_payload(item, request) for item in startups]})

    def patch(self, request, startup_id):
        startup = StartupCompany.objects.filter(id=startup_id).select_related("user").first()
        decision = request.data.get("status")
        if not startup or decision not in ["Approved", "Rejected"]:
            return Response({"error": "Valid startup and decision are required."}, status=status.HTTP_400_BAD_REQUEST)
        if decision == "Approved" and startup.fayda_status != "Approved":
            return Response({"error": "Approve the founder’s Fayda identity first."}, status=status.HTTP_400_BAD_REQUEST)
        startup.company_status = decision
        startup.save(update_fields=["company_status"])
        return Response({"message": f"Startup {decision.lower()}.", "startup": startup_payload(startup, request)})


class UserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.order_by("-date_joined")
        return Response({"users": [{"id": str(item.id), "full_name": item.full_name or "", "email": item.email, "phone_number": item.phone_number or "", "is_active": item.is_active, "is_staff": item.is_staff, "date_joined": item.date_joined, "startup_count": item.startupcompany_set.count(), "campaign_count": item.campaign_set.count()} for item in users]})


class UserDetailView(APIView):
    permission_classes = [IsAdminUser]

    def patch(self, request, user_id):
        user = User.objects.filter(id=user_id).first()
        if not user:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.id == request.user.id and request.data.get("is_active") is False:
            return Response({"error": "You cannot deactivate your own admin account."}, status=status.HTTP_400_BAD_REQUEST)
        if "is_active" in request.data:
            user.is_active = bool(request.data["is_active"])
        user.save(update_fields=["is_active"])
        return Response({"message": "User updated.", "id": str(user.id), "is_active": user.is_active})


class WithdrawalManagementView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, withdrawal_id=None):
        items = WithdrawalRequest.objects.select_related("campaign", "requester").order_by("-created_at")
        return Response({"withdrawals": [withdrawal_payload(item) for item in items]})

    def patch(self, request, withdrawal_id):
        item = WithdrawalRequest.objects.filter(id=withdrawal_id).select_related("campaign", "requester").first()
        next_status = request.data.get("status")
        if not item or next_status not in dict(WithdrawalRequest.STATUS_CHOICES):
            return Response({"error": "Valid withdrawal request and status are required."}, status=status.HTTP_400_BAD_REQUEST)
        transitions = {
            "Pending": {"Processing", "Rejected"},
            "Processing": {"Completed", "Rejected"},
            "Completed": set(),
            "Rejected": set(),
        }
        if next_status != item.status and next_status not in transitions[item.status]:
            return Response({"error": f"A {item.status.lower()} request cannot be moved to {next_status.lower()}."}, status=status.HTTP_400_BAD_REQUEST)
        item.status = next_status
        item.save(update_fields=["status", "updated_at"])
        return Response({"message": "Withdrawal status updated.", "withdrawal": withdrawal_payload(item)})


class CampaignMonitorView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, campaign_id=None):
        campaigns = Campaign.objects.select_related("campaign_creator", "startup_company", "category").order_by("-created_at")
        return Response({"campaigns": [campaign_payload(item) for item in campaigns]})

    def patch(self, request, campaign_id):
        campaign = Campaign.objects.filter(id=campaign_id).select_related("campaign_creator", "startup_company", "category").first()
        decision = request.data.get("status")
        allowed = [item[0] for item in Campaign.campaign_status_choice]
        if not campaign or decision not in allowed:
            return Response({"error": "Valid campaign and status are required."}, status=status.HTTP_400_BAD_REQUEST)
        if decision == "Approved" and (not campaign.startup_company or campaign.startup_company.company_status != "Approved"):
            return Response({"error": "The startup must be approved first."}, status=status.HTTP_400_BAD_REQUEST)
        campaign.campaign_status = decision
        campaign.is_active = decision not in ["Rejected", "suspended"]
        campaign.save(update_fields=["campaign_status", "is_active"])
        return Response({"message": "Campaign status updated.", "campaign": campaign_payload(campaign)})
