from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fund_rasing", "0010_normalize_media_upload_paths")]

    operations = [
        migrations.AddField(
            model_name="fundtransaction",
            name="contribution_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
