from django.db import models
import uuid
from accounts.models import User


class CampaignCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()

class Campaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(CampaignCategory, on_delete=models.CASCADE)
    campaign_creator = models.ForeignKey(User,on_delete=models.PROTECT)
    campaign_title = models.CharField(max_length=220)
    creator_type = models.CharField(max_length=220, default='Startup')
    short_code = models.CharField(max_length=220, unique=True, null=True, blank=True)
    campaign_description = models.TextField()
    cover_image = models.ImageField(upload_to='media/campaign_cover_images/')
    startup_company = models.ForeignKey('startup_company.StartupCompany', on_delete=models.CASCADE, null=True, blank=True)
    individual = models.ForeignKey('individual.Individual', on_delete=models.CASCADE, null=True, blank=True)
    demo = models.ForeignKey('startup_company.DemovideoandImage', on_delete=models.CASCADE, null=True, blank=True)
    progress = models.ForeignKey('startup_company.ProgressVideoandImage', on_delete=models.CASCADE, null=True, blank=True)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    campaign_status_choice = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Paused', 'Paused'),
        ('Completed', 'Completed'),
        ('suspended', 'Suspended'),
        ('Rejected', 'Rejected'),
    ]
    campaign_status = models.CharField(max_length=20, choices=campaign_status_choice, default='Pending')
    location = models.CharField(max_length=255,null=True, blank=True)

class Donation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    donor = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)
    name = models.CharField(max_length=220, null=True, blank=True)
    is_anonymous = models.BooleanField(default=False)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CampaignMedia(models.Model):
    MEDIA_TYPES = [("image", "Image"), ("video", "Video")]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="demo_media")
    file = models.FileField(upload_to="media/campaign_demos/")
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)


class CampaignLike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="campaign_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["campaign", "user"], name="unique_campaign_like"),
        ]

    
class FundTransaction(models.Model):
    transaction_status = [
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected'),
        ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    donation = models.OneToOneField(Donation, on_delete=models.CASCADE)
    payment_gateway = models.CharField(max_length=220)
    transaction_id = models.CharField(max_length=220,unique=True)
    is_paid = models.BooleanField(default=False)
    transaction_date = models.DateTimeField(auto_now_add=True)
    transaction_fee = models.DecimalField(max_digits=10,decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10,decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=transaction_status, default='Pending')
    currency = models.CharField(max_length=3, default="ETB")
    contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    charged_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    swap_status = models.CharField(max_length=20, default="Not required")
    swap_amount_etb = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    swap_response = models.JSONField(default=dict, blank=True)
    swap_attempted_at = models.DateTimeField(null=True, blank=True)

class ReportCampaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE,null=True, blank=True)
    name = models.CharField(max_length=220, null=True, blank=True)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class WithdrawalRequest(models.Model):
    BANK_CHOICES = [
        ("CBE", "Commercial Bank of Ethiopia (CBE)"),
        ("Abyssinia", "Bank of Abyssinia"),
        ("Awash", "Awash Bank"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Processing", "Processing"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.PROTECT, related_name="withdrawal_requests")
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name="withdrawal_requests")
    bank_name = models.CharField(max_length=32, choices=BANK_CHOICES)
    account_number = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ContactMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    comment_status_choice = [
        ('Pending', 'Pending'),
        ('Seen', 'Seen'),
    ]
    comment_status = models.CharField(max_length=20, choices=comment_status_choice, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
