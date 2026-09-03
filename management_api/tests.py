from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from accounts.models import User
from fund_rasing.models import Campaign, CampaignCategory, Donation, WithdrawalRequest
from startup_company.models import StartupCompany


class ManagementApiTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@asjemari.et",
            password="admin-password",
            full_name="Platform Admin",
            is_staff=True,
        )
        self.founder = User.objects.create_user(
            email="founder@asjemari.et",
            password="founder-password",
            full_name="Startup Founder",
        )

    def test_management_endpoints_require_staff_access(self):
        self.client.force_authenticate(self.founder)
        response = self.client.get("/api/management/overview/")
        self.assertEqual(response.status_code, 403)

    def test_staff_can_manage_categories(self):
        self.client.force_authenticate(self.admin)
        created = self.client.post(
            "/api/management/categories/",
            {"name": "Agriculture", "description": "Food and farming startups."},
            format="json",
        )
        self.assertEqual(created.status_code, 201)

        listed = self.client.get("/api/management/categories/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["categories"][0]["name"], "Agriculture")

    def test_approval_flow_requires_fayda_before_startup_and_startup_before_campaign(self):
        startup = StartupCompany.objects.create(
            user=self.founder,
            fayda_number="1234567890123456",
            company_name="Blue Nile Labs",
            company_description="Water technology",
            company_website="https://example.com",
            company_email="team@example.com",
            company_phone_number="0911234567",
            location="Addis Ababa",
            tin="TIN-9001",
            Traction_describtion="Pilot launched",
            pitch_deck=SimpleUploadedFile("blue-nile.pdf", b"%PDF test", content_type="application/pdf"),
        )
        category = CampaignCategory.objects.create(name="Climate", description="Climate technology")
        campaign = Campaign.objects.create(
            category=category,
            campaign_creator=self.founder,
            campaign_title="Clean water for communities",
            campaign_description="Local purification systems",
            startup_company=startup,
            target_amount=Decimal("100000.00"),
        )
        Donation.objects.create(campaign=campaign, name="Anonymous", amount=Decimal("2500.00"))
        self.client.force_authenticate(self.admin)

        blocked_startup = self.client.patch(
            f"/api/management/startups/{startup.id}/", {"status": "Approved"}, format="json"
        )
        self.assertEqual(blocked_startup.status_code, 400)

        fayda = self.client.patch(
            f"/api/management/fayda/{startup.id}/", {"status": "Approved"}, format="json"
        )
        self.assertEqual(fayda.status_code, 200)

        startup_approval = self.client.patch(
            f"/api/management/startups/{startup.id}/", {"status": "Approved"}, format="json"
        )
        self.assertEqual(startup_approval.status_code, 200)

        startup_list = self.client.get("/api/management/startups/")
        application = startup_list.data["startups"][0]
        self.assertEqual(application["tin"], "TIN-9001")
        self.assertEqual(application["traction_description"], "Pilot launched")
        self.assertEqual(application["company_phone_number"], "0911234567")
        self.assertTrue(application["pitch_deck"])
        self.assertTrue(application["pitch_deck_name"].startswith("blue-nile"))
        self.assertTrue(application["pitch_deck_name"].endswith(".pdf"))

        campaign_approval = self.client.patch(
            f"/api/management/campaigns/{campaign.id}/", {"status": "Approved"}, format="json"
        )
        self.assertEqual(campaign_approval.status_code, 200)

        overview = self.client.get("/api/management/overview/")
        self.assertEqual(overview.status_code, 200)
        self.assertEqual(overview.data["total_raised"], "2500")

        campaigns = self.client.get("/api/management/campaigns/")
        self.assertEqual(campaigns.data["campaigns"][0]["contribution_count"], 1)
        self.assertEqual(campaigns.data["campaigns"][0]["raised_amount"], "2500")

    def test_admin_cannot_deactivate_their_own_account(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/management/users/{self.admin.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_admin_can_process_withdrawal_request_in_order(self):
        category = CampaignCategory.objects.create(name="Technology", description="Technology")
        campaign = Campaign.objects.create(
            category=category,
            campaign_creator=self.founder,
            campaign_title="Founder campaign",
            campaign_description="Campaign details",
            target_amount=Decimal("10000.00"),
            campaign_status="Approved",
        )
        item = WithdrawalRequest.objects.create(
            campaign=campaign,
            requester=self.founder,
            bank_name="Abyssinia",
            account_number="123456789012",
            amount=Decimal("2500.00"),
        )
        self.client.force_authenticate(self.admin)

        processing = self.client.patch(
            f"/api/management/withdrawals/{item.id}/", {"status": "Processing"}, format="json"
        )
        self.assertEqual(processing.status_code, 200)
        self.assertEqual(processing.data["withdrawal"]["status"], "Processing")

        completed = self.client.patch(
            f"/api/management/withdrawals/{item.id}/", {"status": "Completed"}, format="json"
        )
        self.assertEqual(completed.status_code, 200)
