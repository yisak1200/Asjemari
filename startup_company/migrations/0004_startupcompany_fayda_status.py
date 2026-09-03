from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("startup_company", "0003_fayda_startup_verification")]

    operations = [
        migrations.AddField(
            model_name="startupcompany",
            name="fayda_status",
            field=models.CharField(choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending", max_length=20),
        ),
    ]
