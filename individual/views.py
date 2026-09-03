from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Individual
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
# Create your views here.

class CreateIndividualView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        kyc_id = request.data.get('kyc_id')
        name = request.data.get('name')
        description = request.data.get('description')
        website = request.data.get('website')
        email = request.data.get('email')
        phone_number = request.data.get('phone_number')
        # traction_describtion = request.data.get('Traction_describtion')

        if not kyc_id or not name or not description:
            return Response({"error": "kyc_id, name, and description are required fields."}, status=status.HTTP_400_BAD_REQUEST)

        individual = Individual.objects.create(
            user=user,
            kyc_id=kyc_id,
            name=name,
            description=description,
            website=website,
            email=email,
            phone_number=phone_number,
            # Traction_describtion=Traction_describtion
        )
        return Response({"message": "Individual profile created successfully.", "individual_id": str(individual.id)}, status=status.HTTP_201_CREATED)