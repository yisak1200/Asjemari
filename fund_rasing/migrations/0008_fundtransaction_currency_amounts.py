from decimal import Decimal

from django.db import migrations, models


def populate_payment_amounts(apps, schema_editor):
    FundTransaction = apps.get_model("fund_rasing", "FundTransaction")
    for payment in FundTransaction.objects.select_related("donation").all().iterator():
        payment.currency = "ETB"
        payment.contribution_amount = payment.donation.amount
        payment.charged_amount = payment.donation.amount
        payment.exchange_rate = Decimal("1")
        payment.save(update_fields=["currency", "contribution_amount", "charged_amount", "exchange_rate"])


class Migration(migrations.Migration):
    dependencies = [("fund_rasing", "0007_withdrawalrequest")]

    operations = [
        migrations.AddField(model_name="fundtransaction", name="currency", field=models.CharField(default="ETB", max_length=3)),
        migrations.AddField(model_name="fundtransaction", name="contribution_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="fundtransaction", name="charged_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="fundtransaction", name="exchange_rate", field=models.DecimalField(decimal_places=4, default=1, max_digits=12)),
        migrations.RunPython(populate_payment_amounts, migrations.RunPython.noop),
    ]
