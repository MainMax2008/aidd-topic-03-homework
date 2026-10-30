from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def populate_transaction_totals(apps, schema_editor):
    transaction_model = apps.get_model("dashboard", "PortfolioTransaction")
    database = schema_editor.connection.alias
    batch = []

    for portfolio_transaction in (
        transaction_model.objects.using(database)
        .only("pk", "price", "quantity")
        .iterator()
    ):
        portfolio_transaction.total_amount = (
            portfolio_transaction.price * portfolio_transaction.quantity
        )
        batch.append(portfolio_transaction)
        if len(batch) == 1000:
            transaction_model.objects.using(database).bulk_update(
                batch, ("total_amount",)
            )
            batch.clear()

    if batch:
        transaction_model.objects.using(database).bulk_update(
            batch, ("total_amount",)
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("dashboard", "0008_portfolio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="portfolio",
            name="balance",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("100000.00"),
                max_digits=14,
            ),
        ),
        migrations.AddField(
            model_name="portfolio",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="position",
            name="quantity",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="position",
            name="average_buy_price",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=12,
            ),
        ),
        migrations.AlterField(
            model_name="position",
            name="share",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="positions",
                to="dashboard.share",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="position",
            name="position_quantity_positive",
        ),
        migrations.AlterField(
            model_name="portfoliotransaction",
            name="quantity",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="portfoliotransaction",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
        migrations.AddField(
            model_name="portfoliotransaction",
            name="total_amount",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                max_digits=14,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(
            populate_transaction_totals,
            migrations.RunPython.noop,
        ),
    ]
