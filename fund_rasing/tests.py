from rest_framework import status
from rest_framework.test import APITestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from unittest.mock import patch

from accounts.models import User
from startup_company.models import StartupCompany
from .chapa import reconcile_transaction
from .models import Campaign, CampaignCategory, CampaignLike, CampaignMedia, Donation, FundTransaction, ReportCampaign, WithdrawalRequest


class CampaignManagementTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="creator@example.com", password="StrongPass123!", full_name="Campaign Creator")
        self.category = CampaignCategory.objects.create(name="Technology", description="Technology campaigns")
        self.campaign = Campaign.objects.create(
            category=self.category,
            campaign_creator=self.user,
            campaign_title="Original campaign",
            campaign_description="Original story",
            cover_image="media/campaign_cover_images/test.jpg",
            target_amount=100000,
            location="Addis Ababa",
            campaign_status="Approved",
        )
        Donation.objects.create(campaign=self.campaign, name="Supporter One", amount=2500, comment="Keep building!")
        Donation.objects.create(campaign=self.campaign, amount=1500, is_anonymous=True)
        self.client.force_authenticate(self.user)

    def test_create_campaign_accepts_multiple_demo_files(self):
        StartupCompany.objects.create(
            user=self.user,
            fayda_number="987654321000",
            company_name="Creator Startup",
            company_description="A verified startup.",
            Traction_describtion="Growing quickly.",
            pitch_deck="media/pitch_decks/test.pdf",
            company_status="Approved",
        )
        cover = SimpleUploadedFile("cover.jpg", b"cover", content_type="image/jpeg")
        photo = SimpleUploadedFile("demo.jpg", b"photo", content_type="image/jpeg")
        video = SimpleUploadedFile("demo.mp4", b"video", content_type="video/mp4")
        response = self.client.post("/api/campaigns/create/", {
            "title": "Campaign with demos",
            "description": "A campaign containing multiple demo assets.",
            "category": "Technology",
            "target_amount": "250000",
            "location": "Addis Ababa",
            "cover_image": cover,
            "demo_media": [photo, video],
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CampaignMedia.objects.filter(campaign_id=response.data["campaign_id"]).count(), 2)

    def test_owner_can_view_progress_edit_and_list_contributions(self):
        campaigns = self.client.get("/api/campaigns/mine/")
        self.assertEqual(campaigns.status_code, status.HTTP_200_OK)
        self.assertEqual(campaigns.data["campaigns"][0]["raised_amount"], "4000")
        self.assertEqual(campaigns.data["campaigns"][0]["contribution_count"], 2)

        updated = self.client.patch(f"/api/campaigns/{self.campaign.id}/manage/", {"title": "Updated campaign", "target_amount": "120000"}, format="json")
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data["campaign"]["title"], "Updated campaign")

        contributions = self.client.get(f"/api/campaigns/{self.campaign.id}/contributions/")
        self.assertEqual(contributions.status_code, status.HTTP_200_OK)
        self.assertEqual(len(contributions.data["contributions"]), 2)

    def test_approved_campaigns_are_listed_with_cover_and_toggle_likes(self):
        self.campaign.is_active = False
        self.campaign.save(update_fields=["is_active"])

        discovery = self.client.get("/api/campaigns/")
        self.assertEqual(discovery.status_code, status.HTTP_200_OK)
        self.assertEqual(len(discovery.data["campaigns"]), 1)
        self.assertTrue(discovery.data["campaigns"][0]["cover_image"])
        self.assertEqual(discovery.data["campaigns"][0]["like_count"], 0)

        liked = self.client.post(f"/api/campaigns/{self.campaign.id}/like/")
        self.assertEqual(liked.data, {"liked": True, "like_count": 1})
        self.assertTrue(CampaignLike.objects.filter(campaign=self.campaign, user=self.user).exists())

        unliked = self.client.post(f"/api/campaigns/{self.campaign.id}/like/")
        self.assertEqual(unliked.data, {"liked": False, "like_count": 0})

    def test_public_detail_includes_media_pitch_deck_and_safe_contributor_names(self):
        startup = StartupCompany.objects.create(
            user=self.user,
            fayda_number="987654321001",
            company_name="Campaign Company",
            company_description="The company behind the campaign.",
            Traction_describtion="Serving its first customers.",
            pitch_deck=SimpleUploadedFile("campaign-deck.pdf", b"%PDF-1.4 test deck", content_type="application/pdf"),
            company_status="Approved",
        )
        self.campaign.startup_company = startup
        self.campaign.save(update_fields=["startup_company"])
        CampaignMedia.objects.create(
            campaign=self.campaign,
            file=SimpleUploadedFile("demo.jpg", b"demo image", content_type="image/jpeg"),
            media_type="image",
        )
        CampaignMedia.objects.create(
            campaign=self.campaign,
            file=SimpleUploadedFile("demo.mp4", b"demo video", content_type="video/mp4"),
            media_type="video",
        )

        response = self.client.get(f"/api/campaigns/{self.campaign.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["demo_media"]), 2)
        self.assertTrue(response.data["pitch_deck"]["name"].startswith("campaign-deck"))
        self.assertTrue(response.data["pitch_deck"]["name"].endswith(".pdf"))
        self.assertEqual(response.data["startup"]["name"], "Campaign Company")
        names = [item["name"] for item in response.data["recent_contributions"]]
        self.assertIn("Supporter One", names)
        self.assertIn("Anonymous supporter", names)
        anonymous = next(item for item in response.data["recent_contributions"] if item["anonymous"])
        self.assertEqual(anonymous["name"], "Anonymous supporter")

        deck = self.client.get(f"/api/campaigns/{self.campaign.id}/pitch-deck/")
        self.assertEqual(deck.status_code, status.HTTP_200_OK)
        self.assertEqual(deck["Content-Type"], "application/pdf")
        self.assertNotIn("X-Frame-Options", deck)

    def test_owner_can_only_delete_campaign_with_zero_funded_amount(self):
        funded_delete = self.client.delete(f"/api/campaigns/{self.campaign.id}/manage/")
        self.assertEqual(funded_delete.status_code, status.HTTP_400_BAD_REQUEST)

        empty_campaign = Campaign.objects.create(
            category=self.category,
            campaign_creator=self.user,
            campaign_title="Empty campaign",
            campaign_description="No funding yet.",
            cover_image="media/campaign_cover_images/empty.jpg",
            target_amount=50000,
            campaign_status="Pending",
        )
        empty_delete = self.client.delete(f"/api/campaigns/{empty_campaign.id}/manage/")
        self.assertEqual(empty_delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Campaign.objects.filter(id=empty_campaign.id).exists())

    def test_campaign_can_be_reported(self):
        response = self.client.post(f"/api/campaigns/{self.campaign.id}/report/", {
            "reason": "The campaign description contains misleading claims.",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ReportCampaign.objects.filter(campaign=self.campaign, reporter=self.user).exists())

    def test_creator_can_request_available_balance_and_track_status(self):
        response = self.client.post("/api/campaigns/withdrawals/", {
            "campaign_id": str(self.campaign.id),
            "bank_name": "CBE",
            "account_number": "1000123456789",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["withdrawal"]["amount"], "4000")
        self.assertEqual(response.data["withdrawal"]["status"], "Pending")
        self.assertTrue(WithdrawalRequest.objects.filter(campaign=self.campaign, requester=self.user).exists())

        duplicate = self.client.post("/api/campaigns/withdrawals/", {
            "campaign_id": str(self.campaign.id),
            "bank_name": "Awash",
            "account_number": "1000123456789",
        }, format="json")
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        history = self.client.get("/api/campaigns/withdrawals/")
        self.assertEqual(history.status_code, status.HTTP_200_OK)
        self.assertEqual(history.data["withdrawals"][0]["bank_label"], "Commercial Bank of Ethiopia (CBE)")

    @patch("fund_rasing.views.initialize_transaction", return_value="https://checkout.chapa.co/checkout/payment/test")
    def test_chapa_payment_initialization_creates_pending_transaction_without_raising_progress(self, initialize):
        response = self.client.post(f"/api/campaigns/{self.campaign.id}/payments/chapa/initialize/", {
            "amount": "750",
            "anonymous": False,
            "name": "Campaign Supporter",
            "email": "supporter@example.com",
            "phone_number": "0911234567",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["checkout_url"], "https://checkout.chapa.co/checkout/payment/test")
        payment = FundTransaction.objects.get(transaction_id=response.data["tx_ref"])
        self.assertEqual(payment.payment_status, "Pending")
        self.assertFalse(payment.is_paid)
        self.assertEqual(self.client.get("/api/campaigns/").data["campaigns"][0]["raised_amount"], "4000")
        payload = initialize.call_args.args[0]
        self.assertEqual(payload["currency"], "ETB")
        self.assertEqual(payload["amount"], "768.75")
        self.assertEqual(payment.contribution_amount, Decimal("750.00"))
        self.assertEqual(payment.transaction_fee, Decimal("18.75"))
        self.assertEqual(payment.charged_amount, Decimal("768.75"))

    @patch("fund_rasing.views.initialize_transaction", return_value="https://checkout.chapa.co/checkout/payment/usd-test")
    def test_usd_payment_stays_uncredited_until_swap_and_charges_fee_in_usd(self, initialize):
        response = self.client.post(f"/api/campaigns/{self.campaign.id}/payments/chapa/initialize/", {
            "amount": "25",
            "currency": "USD",
            "anonymous": True,
            "email": "supporter@example.com",
            "phone_number": "0911234567",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        payment = FundTransaction.objects.get(transaction_id=response.data["tx_ref"])
        self.assertEqual(payment.donation.amount, Decimal("0.00"))
        self.assertEqual(payment.transaction_fee, Decimal("0.63"))
        self.assertEqual(payment.charged_amount, Decimal("25.63"))
        self.assertEqual(payment.exchange_rate, Decimal("0"))
        payload = initialize.call_args.args[0]
        self.assertEqual(payload["currency"], "USD")
        self.assertEqual(payload["amount"], "25.63")

    def test_payment_options_always_enables_usd(self):
        response = self.client.get("/api/campaigns/payments/chapa/options/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fee_rate"], "0.025")
        self.assertTrue(response.data["currencies"][1]["enabled"])
        self.assertIsNone(response.data["currencies"][1]["etb_rate"])

    @patch("fund_rasing.chapa.swap_usd_to_etb")
    @patch("fund_rasing.chapa.verify_transaction")
    def test_verified_usd_payment_swaps_once_and_credits_etb_progress(self, verify, swap):
        donation = Donation.objects.create(campaign=self.campaign, amount=0)
        payment = FundTransaction.objects.create(
            donation=donation,
            payment_gateway="Chapa",
            transaction_id="asj-test-usd-paid",
            balance=0,
            currency="USD",
            contribution_amount=Decimal("25"),
            transaction_fee=Decimal("0.63"),
            charged_amount=Decimal("25.63"),
            exchange_rate=Decimal("0"),
        )
        verify.return_value = {"status": "success", "data": {
            "status": "success",
            "tx_ref": "asj-test-usd-paid",
            "currency": "USD",
            "amount": "25.63",
        }}
        swap.return_value = {"status": "success", "data": {
            "converted_amount": "3500.00",
            "exchange_rate": "140",
        }}

        reconciled = reconcile_transaction("asj-test-usd-paid")
        self.assertTrue(reconciled.is_paid)
        self.assertEqual(reconciled.payment_status, "Approved")
        self.assertEqual(reconciled.swap_status, "Completed")
        self.assertEqual(reconciled.swap_amount_etb, Decimal("3500.00"))
        self.assertEqual(reconciled.exchange_rate, Decimal("140.0000"))
        self.assertEqual(reconciled.donation.amount, Decimal("3500.00"))

        reconcile_transaction("asj-test-usd-paid")
        swap.assert_called_once_with(Decimal("25"))

    @patch("fund_rasing.chapa.verify_transaction")
    def test_verified_chapa_payment_updates_status_and_campaign_progress(self, verify):
        donation = Donation.objects.create(campaign=self.campaign, name="Paid Supporter", amount=750)
        payment = FundTransaction.objects.create(
            donation=donation,
            payment_gateway="Chapa",
            transaction_id="asj-test-paid",
            balance=0,
            currency="ETB",
            contribution_amount=Decimal("750"),
            transaction_fee=Decimal("18.75"),
            charged_amount=Decimal("768.75"),
            exchange_rate=Decimal("1"),
        )
        verify.return_value = {"status": "success", "data": {
            "status": "success",
            "tx_ref": "asj-test-paid",
            "currency": "ETB",
            "amount": "768.75",
            "charge": "22.50",
        }}
        reconciled = reconcile_transaction("asj-test-paid")
        self.assertTrue(reconciled.is_paid)
        self.assertEqual(reconciled.payment_status, "Approved")
        result = self.client.get("/api/campaigns/payments/chapa/asj-test-paid/")
        self.assertEqual(result.status_code, status.HTTP_200_OK)
        self.assertEqual(result.data["campaign"]["raised_amount"], "4750")
        self.assertEqual(result.data["amount"], "750.00")
        self.assertEqual(result.data["fee_amount"], "18.75")
        self.assertEqual(result.data["charged_amount"], "768.75")

    @patch("fund_rasing.chapa.verify_transaction")
    def test_chapa_verification_rejects_mismatched_amount(self, verify):
        donation = Donation.objects.create(campaign=self.campaign, amount=750)
        FundTransaction.objects.create(donation=donation, payment_gateway="Chapa", transaction_id="asj-test-mismatch", balance=0)
        verify.return_value = {"status": "success", "data": {
            "status": "success",
            "tx_ref": "asj-test-mismatch",
            "currency": "ETB",
            "amount": "1.00",
        }}
        payment = reconcile_transaction("asj-test-mismatch")
        self.assertFalse(payment.is_paid)
        self.assertEqual(payment.payment_status, "Rejected")

    @patch("fund_rasing.chapa.verify_transaction")
    def test_chapa_combined_failed_cancelled_status_is_final(self, verify):
        donation = Donation.objects.create(campaign=self.campaign, amount=500)
        FundTransaction.objects.create(donation=donation, payment_gateway="Chapa", transaction_id="asj-test-cancelled", balance=0)
        verify.return_value = {"status": "success", "data": {
            "status": "failed/cancelled",
            "tx_ref": "asj-test-cancelled",
            "currency": "ETB",
            "amount": "500.00",
        }}
        payment = reconcile_transaction("asj-test-cancelled")
        self.assertFalse(payment.is_paid)
        self.assertEqual(payment.payment_status, "Rejected")
