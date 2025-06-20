# Generated by Django 5.2 on 2025-05-13 13:24

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_productimage_color"),
        ("variation", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductVariation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "price_difference",
                    models.DecimalField(decimal_places=2, default=0.0, max_digits=8),
                ),
                (
                    "option",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="variation.variationoption",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="variations",
                        to="store.product",
                    ),
                ),
            ],
            options={
                "unique_together": {("product", "option")},
            },
        ),
    ]
