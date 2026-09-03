from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("startup_company", "0004_startupcompany_fayda_status")]

    operations = [
        migrations.AddField(
            model_name="startupcompany",
            name="fayda_front_image",
            field=models.ImageField(blank=True, null=True, upload_to="media/fayda_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])]),
        ),
        migrations.AddField(
            model_name="startupcompany",
            name="fayda_back_image",
            field=models.ImageField(blank=True, null=True, upload_to="media/fayda_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])]),
        ),
    ]
