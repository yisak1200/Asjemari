from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from .models import StartupCompany


class StartupApplicationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        saved_identity = StartupCompany.objects.filter(user=request.user).filter(
            Q(fayda_front_image__isnull=False, fayda_back_image__isnull=False)
            | (Q(fayda_number__isnull=False) & ~Q(fayda_number=""))
        ).first()
        required = ["company_name", "company_description", "tin", "traction_description"]
        missing = [field for field in required if not request.data.get(field)]
        if missing or not request.FILES.get("pitch_deck"):
            return Response({"error": "Complete every required startup and Fayda field."}, status=status.HTTP_400_BAD_REQUEST)
        if not saved_identity and (not request.FILES.get("fayda_front_image") or not request.FILES.get("fayda_back_image")):
            return Response({"error": "Upload clear images of the front and back of your Fayda ID."}, status=status.HTTP_400_BAD_REQUEST)

        startup = StartupCompany.objects.create(
            user=request.user,
            fayda_number=None,
            fayda_front_image=None if saved_identity else request.FILES["fayda_front_image"],
            fayda_back_image=None if saved_identity else request.FILES["fayda_back_image"],
            company_name=request.data["company_name"],
            company_description=request.data["company_description"],
            company_website=request.data.get("company_website") or None,
            company_email=request.user.email,
            company_phone_number=request.data.get("company_phone_number") or None,
            location=request.data.get("location") or None,
            tin=request.data["tin"],
            Traction_describtion=request.data["traction_description"],
            pitch_deck=request.FILES["pitch_deck"],
            company_status="Pending",
        )
        return Response({"message": "Startup verification submitted.", "startup_id": str(startup.id), "status": startup.company_status}, status=status.HTTP_201_CREATED)


class StartupStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        startups = StartupCompany.objects.filter(user=request.user).order_by("company_name")
        if not startups.exists():
            return Response({"status": "Not submitted", "can_create_campaign": False, "fayda_saved": False, "companies": []})
        companies = [{"id": str(item.id), "name": item.company_name, "status": item.company_status, "location": item.location or ""} for item in startups]
        approved = startups.filter(company_status="Approved")
        latest = startups.order_by("-id").first()
        return Response({
            "status": "Approved" if approved.exists() else latest.company_status,
            "can_create_campaign": approved.exists(),
            "fayda_saved": startups.filter(
                Q(fayda_front_image__isnull=False, fayda_back_image__isnull=False)
                | (Q(fayda_number__isnull=False) & ~Q(fayda_number=""))
            ).exists(),
            "companies": companies,
        })
