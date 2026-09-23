from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fund_rasing", "0009_fundtransaction_swap_tracking")]

    operations = [
        migrations.AlterField(
            model_name="campaign",
            name="cover_image",
            field=models.ImageField(upload_to="campaign_cover_images/"),
        ),
        migrations.AlterField(
            model_name="campaignmedia",
            name="file",
            field=models.FileField(upload_to="campaign_demos/"),
        ),
    ]
