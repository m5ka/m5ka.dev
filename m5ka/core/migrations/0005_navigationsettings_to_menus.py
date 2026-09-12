import uuid

from django.conf import settings
from django.db import migrations
from wagtail.coreutils import get_supported_content_language_variant

HANDLE_FIELDS = {
    "header": "header_links",
    "hamburger": "hamburger_links",
    "footer": "footer_links",
}


def get_default_locale(apps):
    Locale = apps.get_model("wagtailcore", "Locale")
    language_code = get_supported_content_language_variant(settings.LANGUAGE_CODE)
    return (
        Locale.objects.filter(language_code=language_code).first()
        or Locale.objects.order_by("pk").first()
    )


def navigation_settings_to_menus(apps, schema_editor):
    NavigationSettings = apps.get_model("m5ka_core", "NavigationSettings")
    Menu = apps.get_model("m5ka_core", "Menu")
    MenuItem = apps.get_model("m5ka_core", "MenuItem")
    Page = apps.get_model("wagtailcore", "Page")

    navigation = NavigationSettings.objects.first()
    locale = get_default_locale(apps)
    if navigation is None or locale is None:
        return

    for handle, field_name in HANDLE_FIELDS.items():
        page_ids = [
            block["value"]
            for block in getattr(navigation, field_name).raw_data
            if block["type"] == "page" and block["value"]
        ]
        existing_ids = set(
            Page.objects.filter(pk__in=page_ids).values_list("pk", flat=True)
        )
        page_ids = [page_id for page_id in page_ids if page_id in existing_ids]
        if not page_ids:
            continue

        menu = Menu.objects.create(
            handle=handle, locale=locale, translation_key=uuid.uuid4()
        )
        MenuItem.objects.bulk_create(
            MenuItem(
                menu=menu,
                page_id=page_id,
                sort_order=sort_order,
                locale=locale,
                translation_key=uuid.uuid4(),
            )
            for sort_order, page_id in enumerate(page_ids)
        )


def menus_to_navigation_settings(apps, schema_editor):
    NavigationSettings = apps.get_model("m5ka_core", "NavigationSettings")
    Menu = apps.get_model("m5ka_core", "Menu")

    locale = get_default_locale(apps)
    if locale is None:
        return

    navigation = NavigationSettings.objects.first() or NavigationSettings()
    for handle, field_name in HANDLE_FIELDS.items():
        menu = Menu.objects.filter(handle=handle, locale=locale).first()
        items = menu.items.order_by("sort_order") if menu else []
        setattr(
            navigation,
            field_name,
            [
                {"type": "page", "value": item.page_id, "id": str(uuid.uuid4())}
                for item in items
            ],
        )
    navigation.save()
    Menu.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("m5ka_core", "0004_menu_menuitem")]

    operations = [
        migrations.RunPython(navigation_settings_to_menus, menus_to_navigation_settings)
    ]
