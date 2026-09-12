from django import template

from m5ka.core.models import Menu

register = template.Library()


@register.simple_tag
def menu_links(handle):
    return Menu.get_links(handle)
