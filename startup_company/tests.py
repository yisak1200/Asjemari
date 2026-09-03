from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from .models import StartupCompany


class StartupWorkflowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="startup@example.com", password="StrongPass123!", full_name="Startup Founder")
        self.client.force_authenticate(self.user)

    def test_fayda_application_then_campaign_gate(self):
        pitch = SimpleUploadedFile("pitch.pdf", b"pitch deck", content_type="application/pdf")
        fayda_front = SimpleUploadedFile("fayda-front.jpg", b"front", content_type="image/jpeg")
        fayda_back = SimpleUploadedFile("fayda-back.jpg", b"back", content_type="image/jpeg")
        response = self.client.post("/api/startups/apply/", {
            "fayda_front_image": fayda_front,
            "fayda_back_image": fayda_back,
            "company_name": "Test Startup",
            "company_description": "A startup built for testing.",
            "tin": "TIN-123",
            "traction_description": "A working pilot.",
            "location": "Addis Ababa",
            "pitch_deck": pitch,
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "Pending")

        blocked = self.client.post("/api/campaigns/create/", {}, format="multipart")
        self.assertEqual(blocked.status_code, status.HTTP_403_FORBIDDEN)

        startup = StartupCompany.objects.get(user=self.user)
        self.assertEqual(startup.tin, "TIN-123")
        startup.company_status = "Approved"
        startup.save(update_fields=["company_status"])

        second_pitch = SimpleUploadedFile("second-pitch.pdf", b"second pitch deck", content_type="application/pdf")
        second = self.client.post("/api/startups/apply/", {
            "company_name": "Second Startup",
            "company_description": "Another company using the saved founder identity.",
            "tin": "TIN-456",
            "traction_description": "Early customers.",
            "location": "Hawassa",
            "pitch_deck": second_pitch,
        }, format="multipart")
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)

        status_response = self.client.get("/api/startups/status/")
        self.assertTrue(status_response.data["can_create_campaign"])
        self.assertTrue(status_response.data["fayda_saved"])
        self.assertEqual(len(status_response.data["companies"]), 2)
