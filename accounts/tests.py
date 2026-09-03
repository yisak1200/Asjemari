from rest_framework import status
from rest_framework.test import APITestCase
from accounts.models import User


class EmailAuthenticationTests(APITestCase):
    def test_register_and_login_with_email_and_password(self):
        registration = self.client.post("/api/accounts/register/", {
            "full_name": "Test Founder",
            "email": "founder@example.com",
            "password": "StrongPass123!",
        }, format="json")
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
