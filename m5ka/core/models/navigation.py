from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import (
    CASCADE,
    Case,
    CharField,
    CheckConstraint,
    ForeignKey,
    Prefetch,
    Q,
    UniqueConstraint,
    When,
)
from django.utils.translation import get_language
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail.coreutils import get_supported_content_language_variant
from wagtail.models import Orderable, Page, TranslatableMixin
from wagtail.snippets.models import register_snippet

from m5ka.core.constants import MenuHandle


@dataclass(frozen=True)
class MenuLink:
    page: Page
    text: str


@register_snippet
class Menu(TranslatableMixin, ClusterableModel):
    handle = CharField(max_length=16, choices=MenuHandle.choices)

    panels = [FieldPanel("handle"), InlinePanel("items", heading="Items")]

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=("translation_key", "locale"),
                name="unique_translation_key_locale_m5ka_core_menu",
            ),
            UniqueConstraint(
                fields=("handle", "locale"), name="unique_menu_handle_per_locale"
            ),
            CheckConstraint(
                condition=Q(handle__in=MenuHandle.values), name="valid_menu_handle"
            ),
        ]

    def __str__(self):
        return f"{self.get_handle_display()} ({self.locale})"

    def clean(self):
        super().clean()
        # locale is not a form field, so the admin form skips the
        # (handle, locale) constraint; check it here to avoid an IntegrityError
        if self.locale_id is None:
            return
        duplicates = Menu.objects.filter(handle=self.handle, locale_id=self.locale_id)
        if duplicates.exclude(pk=self.pk).exists():
            raise ValidationError(
                {"handle": "A menu with this handle already exists for this locale."}
            )

    @classmethod
    def get_links(cls, handle):
        """
        Returns the live links for the menu with the given handle in the active
        language, falling back to the default language's menu. Linked pages are
        swapped for their translation in the active language where one is live.
        """
        handle = MenuHandle(handle)
        default_language_code = get_supported_content_language_variant(
            settings.LANGUAGE_CODE
        )
        try:
            language_code = get_supported_content_language_variant(get_language())
        except LookupError:
            language_code = default_language_code

        menu = (
            cls.objects.filter(
                handle=handle,
                locale__language_code__in={language_code, default_language_code},
            )
            .order_by(
                Case(When(locale__language_code=language_code, then=0), default=1)
            )
            .prefetch_related(
                Prefetch("items", MenuItem.objects.select_related("page__locale"))
            )
            .first()
        )
        if menu is None:
            return []

        items = menu.items.all()
        untranslated_keys = {
            item.page.translation_key
            for item in items
            if item.page.locale.language_code != language_code
        }
        translations = {}
        if untranslated_keys:
            translations = {
                page.translation_key: page
                for page in Page.objects.live().filter(
                    translation_key__in=untranslated_keys,
                    locale__language_code=language_code,
                )
            }

        links = []
        for item in items:
            page = translations.get(item.page.translation_key, item.page)
            if page.live:
                links.append(MenuLink(page=page, text=item.label or page.title))
        return links


class MenuItem(TranslatableMixin, Orderable):
    menu = ParentalKey(Menu, on_delete=CASCADE, related_name="items")
    page = ForeignKey("wagtailcore.Page", on_delete=CASCADE, related_name="+")
    label = CharField(
        max_length=64, blank=True, help_text="Defaults to the page's title"
    )

    panels = [FieldPanel("page"), FieldPanel("label")]

    class Meta(Orderable.Meta):
        constraints = [
            UniqueConstraint(
                fields=("translation_key", "locale"),
                name="unique_translation_key_locale_m5ka_core_menuitem",
            )
        ]
