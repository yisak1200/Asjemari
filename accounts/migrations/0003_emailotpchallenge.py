import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_email_authentication")]

    operations = [
        migrations.CreateModel(
            name="EmailOTPChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("purpose", models.CharField(choices=[("signup", "Signup"), ("password_reset", "Password reset")], max_length=24)),
                ("code_hash", models.CharField(max_length=128)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("is_used", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
            ],
            options={
                "db_table": "email_otp_challenges",
                "indexes": [models.Index(fields=["email", "purpose", "created_at"], name="email_otp_lookup_idx")],
            },
        ),
    ]
