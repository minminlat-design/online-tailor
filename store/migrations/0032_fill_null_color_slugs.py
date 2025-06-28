from django.db import migrations
from django.utils.text import slugify


def fill_null_color_slugs(apps, schema_editor):
    """
    Generates a unique slug for every Color that
    currently has slug = NULL or an empty string.
    """
    Color = apps.get_model("store", "Color")

    # Keep a set of slugs that already exist to guarantee uniqueness
    existing_slugs = set(Color.objects.exclude(slug__in=["", None])
                                     .values_list("slug", flat=True))

    # Handle rows with NULL or empty slug
    for color in Color.objects.filter(slug__isnull=True) | Color.objects.filter(slug=""):
        base_slug = slugify(color.name) or "color"  # fallback if name is blank
        slug = base_slug
        counter = 1

        # Ensure uniqueness
        while slug in existing_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1

        color.slug = slug
        color.save(update_fields=["slug"])
        existing_slugs.add(slug)


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0029_brand_slug_color_slug"),   # adjust if your last migration number differs
    ]

    operations = [
        migrations.RunPython(fill_null_color_slugs),
    ]
