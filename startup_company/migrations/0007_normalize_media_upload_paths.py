import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("startup_company", "0006_startupcompany_tin")]

    operations = [
        migrations.AlterField(
            model_name="kycdocument",
            name="startup_certification",
            field=models.ImageField(upload_to="certifications/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]),
        ),
        migrations.AlterField(
            model_name="kycdocument",
            name="License",
            field=models.ImageField(upload_to="licenses/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]),
        ),
        migrations.AlterField(
            model_name="kycdocument",
            name="company_manager_national_id",
            field=models.ImageField(upload_to="national_id_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "svg", "webp", "gif"])]),
        ),
        migrations.AlterField(
            model_name="startupcompany",
            name="fayda_front_image",
            field=models.ImageField(blank=True, null=True, upload_to="fayda_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])]),
        ),
        migrations.AlterField(
            model_name="startupcompany",
            name="fayda_back_image",
            field=models.ImageField(blank=True, null=True, upload_to="fayda_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"])]),
        ),
        migrations.AlterField(
            model_name="startupcompany",
            name="pitch_deck",
            field=models.FileField(upload_to="pitch_decks/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])]),
        ),
        migrations.AlterField(
            model_name="progressvideoandimage",
            name="progress_video",
            field=models.FileField(blank=True, null=True, upload_to="progress_videos/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["mp4", "avi", "mov", "mp3", "wav"])]),
        ),
        migrations.AlterField(
            model_name="progressvideoandimage",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="progress_images/", validators=[django.core.validators.FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png"])]),
        ),
    ]
