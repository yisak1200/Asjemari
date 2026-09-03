from django.db import models
import uuid
from django.core.validators import FileExtensionValidator
from fund_rasing.models import Campaign

class KycDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    startup_certification = models.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        upload_to='media/certifications/')
    License = models.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        upload_to='media/licenses/')
    Tin = models.CharField(max_length=255)
    company_manager_national_id = models.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png','svg','webp','gif'])],
        upload_to='media/national_id_images/'
        )

class StartupCompany(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    kyc = models.OneToOneField(KycDocument, on_delete=models.CASCADE, null=True, blank=True)
    fayda_number = models.CharField(max_length=32, unique=True, null=True)
    fayda_front_image = models.ImageField(
        upload_to='media/fayda_images/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    fayda_back_image = models.ImageField(
        upload_to='media/fayda_images/', null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    fayda_status_choice = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    fayda_status = models.CharField(max_length=20, choices=fayda_status_choice, default='Pending')
    company_name = models.CharField(max_length=255)
    company_description = models.TextField()
    company_website = models.URLField(max_length=200, null=True, blank=True)
    company_email = models.EmailField(null=True, blank=True)
    company_phone_number = models.CharField(max_length=15, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    tin = models.CharField(max_length=64, null=True, blank=True)
    Traction_describtion = models.TextField()
    pitch_deck = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])],
        upload_to='media/pitch_decks/'
        )
    company_status_choice = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    company_status = models.CharField(max_length=20, choices=company_status_choice, default='Pending')
    
    



class DemovideoandImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    demo_video = models.URLField(null=True, blank=True)
    demo_image = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_first_time = models.BooleanField(default=False)


class ProgressVideoandImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    progress_video = models.FileField(
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov','mp3','wav'])],
        upload_to='media/progress_videos/',
        null=True,blank=True
    )
    image = models.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        upload_to='media/progress_images/',
        null=True,blank=True
    )
    progress_update_description = models.TextField(null=True, blank=True)
