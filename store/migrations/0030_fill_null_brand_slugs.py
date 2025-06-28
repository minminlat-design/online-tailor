from django.db import migrations
from django.utils.text import slugify

def fill_null_slugs(apps, schema_editor):
    Brand = apps.get_model('store', 'Brand')
    for brand in Brand.objects.filter(slug__isnull=True) | Brand.objects.filter(slug=''):
        base_slug = slugify(brand.name)
        slug = base_slug
        counter = 1
        while Brand.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        brand.slug = slug
        brand.save()

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0029_brand_slug_color_slug'),  # make sure this matches your last migration
    ]

    operations = [
        migrations.RunPython(fill_null_slugs),
    ]
