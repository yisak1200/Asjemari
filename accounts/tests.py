from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from accounts.models import User


class EmailAuthenticationTests(APITestCase):
    def test_staged_registration_requests_code_before_profile_details(self):
        with patch("accounts.otp.generate_otp_code", return_value="123456"), patch("accounts.otp.send_email"):
            requested = self.client.post(
                "/api/accounts/register/",
                {"email": "staged@example.com"},
                format="json",
            )
        self.assertEqual(requested.status_code, status.HTTP_202_ACCEPTED)

        verified = self.client.post(
            "/api/accounts/register/",
            {"email": "staged@example.com", "otp": "123456"},
            format="json",
        )
        self.assertEqual(verified.status_code, status.HTTP_200_OK)
        self.assertIn("signup_token", verified.data)
        self.assertFalse(User.objects.filter(email="staged@example.com").exists())

        completed = self.client.post(
            "/api/accounts/register/",
            {
                "email": "staged@example.com",
                "signup_token": verified.data["signup_token"],
                "full_name": "Staged Founder",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(completed.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", completed.data)
        self.assertTrue(User.objects.filter(email="staged@example.com", full_name="Staged Founder").exists())

    def test_register_and_login_with_email_and_password(self):
        registration_payload = {
            "full_name": "Test Founder",
            "email": "founder@example.com",
            "password": "StrongPass123!",
        }
        with patch("accounts.otp.generate_otp_code", return_value="123456"), patch("accounts.otp.send_email") as send_email:
            requested = self.client.post("/api/accounts/register/", registration_payload, format="json")
            self.assertEqual(requested.status_code, status.HTTP_202_ACCEPTED)
            self.assertTrue(requested.data["otp_required"])
            self.assertEqual(requested.data["expires_in"], 300)
            self.assertFalse(User.objects.filter(email="founder@example.com").exists())
            send_email.assert_called_once()

        registration = self.client.post(
            "/api/accounts/register/",
            {**registration_payload, "otp": "123456"},
            format="json",
        )
        self.assertEqual(registration.status_code, status.HTTP_201_CREATED)
        self.assertIn("access_token", registration.data)
        self.assertIn("refresh", registration.data)

        refreshed = self.client.post("/api/accounts/refresh/", {"refresh": registration.data["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", refreshed.data)

        login = self.client.post("/api/accounts/login/", {
            "email": "founder@example.com",
            "password": "StrongPass123!",
        }, format="json")
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertEqual(login.data["user"]["email"], "founder@example.com")

        user = User.objects.get(email="founder@example.com")
        self.client.force_authenticate(user)
        profile = self.client.patch("/api/accounts/me/", {"full_name": "Updated Founder", "email": "founder@example.com", "phone_number": "+251911000000"}, format="json")
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        self.assertEqual(profile.data["user"]["full_name"], "Updated Founder")

        wrong_password = self.client.post("/api/accounts/password/", {
            "current_password": "WrongPass123!",
            "new_password": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)

        changed = self.client.post("/api/accounts/password/", {
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(changed.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrongPass456!"))

    def test_forgot_password_requires_a_valid_email_code(self):
        user = User.objects.create_user(
            email="reset@example.com",
            password="StrongPass123!",
            full_name="Reset User",
        )
        with patch("accounts.otp.generate_otp_code", return_value="654321"), patch("accounts.otp.send_email") as send_email:
            requested = self.client.post(
                "/api/accounts/password/forgot/",
                {"email": user.email},
                format="json",
            )
            self.assertEqual(requested.status_code, status.HTTP_200_OK)
            self.assertEqual(requested.data["expires_in"], 300)
            send_email.assert_called_once()

        rejected = self.client.post("/api/accounts/password/reset/", {
            "email": user.email,
            "otp": "000000",
            "new_password": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

        reset = self.client.post("/api/accounts/password/reset/", {
            "email": user.email,
            "otp": "654321",
            "new_password": "NewStrongPass456!",
        }, format="json")
        self.assertEqual(reset.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewStrongPass456!"))
