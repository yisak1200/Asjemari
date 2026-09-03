from django.db import migrations, models
from django.db.models import Q


def preserve_legacy_anonymous_donations(apps, schema_editor):
    Donation = apps.get_model("fund_rasing", "Donation")
    Donation.objects.filter(
        Q(name__isnull=True) | Q(name=""),
        donor__isnull=True,
    ).update(is_anonymous=True)


class Migration(migrations.Migration):
    dependencies = [
        ("fund_rasing", "0005_campaignlike"),
    ]

    operations = [
        migrations.AddField(
            model_name="donation",
            name="is_anonymous",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            preserve_legacy_anonymous_donations,
            migrations.RunPython.noop,
        ),
    ]
