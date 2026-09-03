import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fund_rasing", "0006_donation_is_anonymous"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WithdrawalRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("bank_name", models.CharField(choices=[("CBE", "Commercial Bank of Ethiopia (CBE)"), ("Abyssinia", "Bank of Abyssinia"), ("Awash", "Awash Bank")], max_length=32)),
                ("account_number", models.CharField(max_length=32)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("status", models.CharField(choices=[("Pending", "Pending"), ("Processing", "Processing"), ("Completed", "Completed"), ("Rejected", "Rejected")], default="Pending", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("campaign", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="withdrawal_requests", to="fund_rasing.campaign")),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="withdrawal_requests", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
