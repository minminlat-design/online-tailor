from django import template
from urllib.parse import urlencode

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None




@register.simple_tag(takes_context=True)
def query_string(context, get_params, exclude=""):
    if isinstance(exclude, str):
        exclude = [e.strip() for e in exclude.split(",") if e.strip()]

    params = get_params.copy()
    for key in exclude:
        params.pop(key, None)
    return urlencode(params)