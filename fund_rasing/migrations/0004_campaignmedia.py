import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("fund_rasing", "0003_remove_campaign_current_amount_and_more")]

    operations = [
        migrations.CreateModel(
            name="CampaignMedia",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to="media/campaign_demos/")),
                ("media_type", models.CharField(choices=[("image", "Image"), ("video", "Video")], max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="demo_media", to="fund_rasing.campaign")),
            ],
        ),
    ]
