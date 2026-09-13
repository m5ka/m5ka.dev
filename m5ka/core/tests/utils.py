from django.utils.text import slugify

from m5ka.core.models import BlogPost, Menu, MenuItem, SiteCopy
from m5ka.core.models import Page as ContentPage


def create_page(parent, title, slug=None, live=True, model=ContentPage, **kwargs):
    page = parent.add_child(
        instance=model(title=title, slug=slug or slugify(title), **kwargs)
    )
    if not live:
        page.unpublish()
    return page


def create_post(blog_root, title, slug=None, live=True, **kwargs):
    return create_page(blog_root, title, slug, live, model=BlogPost, **kwargs)


def publish_translation(page, locale, title, copy_parents=False):
    translated = page.copy_for_translation(locale, copy_parents=copy_parents)
    translated.title = title
    translated.save_revision().publish()
    translated.refresh_from_db()
    return translated


def create_menu(handle, locale, *items):
    menu = Menu(handle=handle, locale=locale)
    menu.items = [
        MenuItem(page=page, label=label, sort_order=sort_order)
        for sort_order, (page, label) in enumerate(items)
    ]
    menu.save()
    return menu


def create_site_copy(locale, **kwargs):
    return SiteCopy.objects.create(locale=locale, **kwargs)
