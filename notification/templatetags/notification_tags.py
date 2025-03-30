from django import template

register = template.Library()

@register.filter
def split(value, key):
    return value.split(key)

@register.filter(name='get_item')
def get_item(dictionary, key):
    if dictionary and key:
        try:
            return dictionary.get(key)
        except (KeyError, AttributeError):
            return None
    return None