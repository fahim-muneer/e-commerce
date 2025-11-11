from django import template

register = template.Library()

@register.inclusion_tag('home/includes/breadcrumbs.html')
def render_breadcrumbs(trail):
    """
    Renders a breadcrumb trail based on a list of (Name, URL) tuples.
    Example trail: [('Home', '/'), ('Product Name', None)]
    """
    return {'trail': trail}
