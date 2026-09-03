from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from .models import User


def session_payload(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access_token": str(refresh.access_token),
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name or "",
            "is_staff": user.is_staff,
        },
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        full_name = (request.data.get("full_name") or "").strip()

        if not email or not password or not full_name:
            return Response({"error": "Full name, email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=email).exists():
            return Response({"error": "An account with this email already exists."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password)
        except ValidationError as exc:
            return Response({"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email=email, password=password, full_name=full_name)
        return Response(session_payload(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        password = request.data.get("password") or ""
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user or not user.check_password(password):
            return Response({"error": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(session_payload(user), status=status.HTTP_200_OK)


class RefreshSessionView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data={"refresh": request.data.get("refresh")})
        serializer.is_valid(raise_exception=True)
        return Response({"access_token": serializer.validated_data["access"]})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get("current_password") or ""
        new_password = request.data.get("new_password") or ""
        if not request.user.check_password(current_password):
            return Response({"error": "Your current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        if current_password == new_password:
            return Response({"error": "Choose a new password that is different from your current password."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(new_password, request.user)
        except ValidationError as exc:
            return Response({"error": " ".join(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save(update_fields=["password", "updated_at"])
        return Response({"message": "Password changed successfully. Please sign in again."})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": str(request.user.id),
            "full_name": request.user.full_name or "",
            "email": request.user.email,
            "phone_number": request.user.phone_number or "",
            "date_joined": request.user.date_joined,
        })

    def patch(self, request):
        full_name = (request.data.get("full_name") or "").strip()
        email = (request.data.get("email") or "").strip().lower()
        if not full_name or not email:
            return Response({"error": "Full name and email are required."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=email).exclude(id=request.user.id).exists():
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.full_name = full_name
        request.user.email = email
        request.user.phone_number = request.data.get("phone_number") or None
        request.user.save(update_fields=["full_name", "email", "phone_number", "updated_at"])
        return Response({"message": "Profile updated.", "user": {"id": str(request.user.id), "full_name": full_name, "email": email, "phone_number": request.user.phone_number or ""}})
