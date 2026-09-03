from django.shortcuts import render
from startup_company.models import *
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class GetAllStartupCompaniesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        if request.user.groups.filter(name='Admin').exists():
            startup_companies = StartupCompany.objects.all()
            data = []
            for company in startup_companies:
                data.append({
                    'id': str(company.id),
                    'company_name': company.company_name,
                    'company_description': company.company_description,
                    'company_website': company.company_website,
                    'company_email': company.company_email,
                    'company_phone_number': company.company_phone_number,
                    'category': company.category.name,
                    'traction_describtion': company.Traction_describtion,
                    'target_fund_amount': str(company.target_fund_amount),
                    'fund_used_for': company.fund_used_for,
                    'current_fund_amount': str(company.current_fund_amount),
                    'is_funding_completed': company.is_funding_completed,
                    'is_approved': company.is_approved
                })
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not authorized to view startup companies'}, status=status.HTTP_403_FORBIDDEN)
        
class GetStartupCompanyKycDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        if request.user.groups.filter(name='Admin').exists():
            company_id = request.query_params.get('company_id')
            kyc_document = KycDocument.objects.get(startup_company__id=company_id)
            data = {
                'id': str(kyc_document.id),
                'startup_company': kyc_document.startup_company.company_name,
                'startup_certification': kyc_document.startup_certification.url,
                'License': kyc_document.License.url,
                'Tin': kyc_document.Tin,
                'company_manager_national_id': kyc_document.company_manager_national_id.url
            }
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not authorized to view KYC documents'}, status=status.HTTP_403_FORBIDDEN)

class GetStartupProductDemoVideoAndImageView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        if request.user.groups.filter(name='Admin').exists():
            company_id = request.query_params.get('company_id')
            demo_video_and_image = StartupCompanyProductDemovideoandImage.objects.filter(startup_company__id=company_id)
            data = []
            for item in demo_video_and_image:
                data.append({
                    'id': str(item.id),
                    'startup_company': item.startup_company.company_name,
                    'demo_video': item.demo_video.url,
                    'demo_image': item.demo_image.url
                })
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not authorized to view product demo videos and images'}, status=status.HTTP_403_FORBIDDEN)    

class GetStartupProgressVideoAndImageView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self,request):
        if request.user.groups.filter(name='Admin').exists():
            company_id = request.query_params.get('company_id')
            progress_video_and_image = StartupCompanyProgressVideoandImage.objects.filter(startup_company__id=company_id)
            data = []
            for item in progress_video_and_image:
                data.append({
                    'id': str(item.id),
                    'startup_company': item.startup_company.company_name,
                    'progress_video': item.progress_video.url,
                    'image': item.image.url
                })
            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not authorized to view progress videos and images'}, status=status.HTTP_403_FORBIDDEN)
class StartupCompanyChangeStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self,request):
        if request.user.groups.filter(name='Admin').exists():
            company_id = request.data.get('company_id')
            status = request.data.get('status')
            startup_company = StartupCompany.objects.get(id=company_id)
            if status == 'Approved':
                startup_company.company_status = 'Approved'
                startup_company.save()
                return Response({'message': 'Startup company approved successfully'}, status=status.HTTP_200_OK)
            elif status == 'Rejected':
                 startup_company.company_status = 'Rejected'
                 startup_company.save()
                 return Response({'message': 'Startup company rejected successfully'}, status=status.HTTP_200_OK)
            return Response({'message': 'Startup company status updated successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'User is not authorized to update startup company status'}, status=status.HTTP_403_FORBIDDEN)