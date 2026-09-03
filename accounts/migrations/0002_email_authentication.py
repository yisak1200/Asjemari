from django.db import migrations, models


def populate_missing_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.filter(email__isnull=True):
        user.email = f"legacy-{user.id}@asjemari.local"
        user.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(populate_missing_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, max_length=15, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="user",
            name="pin",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
