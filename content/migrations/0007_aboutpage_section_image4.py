# Generated by Django 5.2 on 2025-06-18 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_aboutpage_section_image1_aboutpage_section_image2_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="aboutpage",
            name="section_image4",
            field=models.ImageField(blank=True, null=True, upload_to="about/"),
        ),
    ]
