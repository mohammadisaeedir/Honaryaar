from django import template

from ejranow import catalog

register = template.Library()


@register.filter
def gender_label(value):
    return catalog.gender_label(value)


@register.filter
def role_title(slug):
    return catalog.role_title(slug)


@register.filter
def category_title(slug):
    return catalog.category_title(slug)


@register.filter
def age_label(item):
    return catalog.age_label(item)


@register.filter
def project_of(slug):
    return catalog.project_by_slug(slug)


@register.simple_tag
def query_string(request, **kwargs):
    params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else request.path
