from django import template 
from orders.constants import COUNTRY_DICT

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})



@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except Exception as e:
        return None
    

@register.filter(name='add_class')
def add_class(field, css):
    try:
        return field.as_widget(attrs={"class": css})
    except AttributeError:
        # If 'field' is already a string (SafeString), just return it
        return field
    

@register.filter
def country_name(code):
    return COUNTRY_DICT.get(code, code)



@register.filter
def dict_get(d, key):
    if isinstance(d, dict):
        return d.get(key)
    return ''


@register.filter
def is_dict(value):
    return isinstance(value, dict)


@register.filter
def get_by_index(sequence, index):
    try:
        return sequence[int(index)]
    except (IndexError, ValueError, TypeError):
        return None
    
    

@register.filter
def get_location_by_pk(queryset, pk):
    try:
        return queryset.get(pk=pk)
    except:
        return None
