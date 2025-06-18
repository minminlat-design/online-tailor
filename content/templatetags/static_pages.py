# content/templatetags/static_pages.py

from django import template
from content.models import StaticPage

register = template.Library()

@register.simple_tag
def get_static_pages():
    return StaticPage.objects.filter(published=True)
