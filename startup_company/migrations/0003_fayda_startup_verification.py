from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("startup_company", "0002_remove_demovideoandimage_campaign_and_more")]

    operations = [
        migrations.AlterField(
            model_name="startupcompany",
            name="kyc",
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="startup_company.kycdocument"),
        ),
        migrations.AddField(
            model_name="startupcompany",
            name="fayda_number",
            field=models.CharField(max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="startupcompany",
            name="location",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
