# Generated by Django 5.2 on 2025-05-04 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0009_remove_product_image"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="productimage",
            options={"ordering": ["order"]},
        ),
        migrations.AddField(
            model_name="productimage",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
