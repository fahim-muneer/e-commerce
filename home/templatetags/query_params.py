from django import template
from django.http import QueryDict

register = template.Library()

@register.simple_tag
def url_replace(request, **kwargs):
    """
    Preserve all existing GET parameters and update/add new ones
    Usage: {% url_replace request page=2 %}
    """
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()

@register.simple_tag
def preserve_params(request, exclude=''):
    """
    Get all current GET parameters except excluded ones
    Usage: {% preserve_params request exclude='page' %}
    """
    query = request.GET.copy()
    exclude_list = [x.strip() for x in exclude.split(',') if x.strip()]
    for key in exclude_list:
        query.pop(key, None)
    return query.urlencode()