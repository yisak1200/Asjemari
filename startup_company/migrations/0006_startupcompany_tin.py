from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("startup_company", "0005_startupcompany_fayda_images"),
    ]

    operations = [
        migrations.AddField(
            model_name="startupcompany",
            name="tin",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
