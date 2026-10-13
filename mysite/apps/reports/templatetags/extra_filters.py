# app/templatetags/extra_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    """
    Access dictionary key or object attribute dynamically
    Usage: {{ row|get_item:col.key }}
    """
    if isinstance(obj, dict):
        return obj.get(key, '')
    return getattr(obj, key, '')




import base64

def get_base64_image(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
