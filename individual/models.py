from django.db import models
import uuid
from startup_company.models import KycDocument
from django.core.validators import FileExtensionValidator

# Create your models here.
class Individual(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    kyc = models.OneToOneField(KycDocument, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    website = models.URLField(max_length=200, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    # Traction_describtion = models.TextField()
    
    individual_status_choice = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    individual_status = models.CharField(max_length=20, choices=individual_status_choice, default='Pending')
    