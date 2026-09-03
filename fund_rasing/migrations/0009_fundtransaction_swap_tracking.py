from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fund_rasing", "0008_fundtransaction_currency_amounts")]

    operations = [
        migrations.AddField(model_name="fundtransaction", name="swap_status", field=models.CharField(default="Not required", max_length=20)),
        migrations.AddField(model_name="fundtransaction", name="swap_amount_etb", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="fundtransaction", name="swap_response", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="fundtransaction", name="swap_attempted_at", field=models.DateTimeField(blank=True, null=True)),
    ]
