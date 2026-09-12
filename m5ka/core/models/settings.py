from django.db.models import (
    SET_NULL,
    CharField,
    ForeignKey,
    TextField,
    UniqueConstraint,
)
from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Locale, TranslatableMixin
from wagtail.snippets.models import register_snippet


@register_snippet
class SiteCopy(TranslatableMixin):
    homepage_heading = CharField(
        max_length=128, blank=True, help_text="A hero heading to appear on the homepage"
    )
    short_bio = TextField(blank=True, help_text="A short bio to appear on the homepage")
    footer_text = RichTextField(features=["bold", "italic", "hr", "link"], blank=True)
    copyright_author = CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=("translation_key", "locale"),
                name="unique_translation_key_locale_m5ka_core_sitecopy",
            ),
            UniqueConstraint(fields=["locale"], name="unique_sitecopy_per_locale"),
        ]

    def __str__(self):
        return str(self.locale)


@register_setting(icon="group")
class SocialSettings(BaseGenericSetting):
    lastfm_username = CharField(
        max_length=128, blank=True, verbose_name="LastFM username"
    )
    github_username = CharField(max_length=128, blank=True)
    linkedin_username = CharField(
        max_length=128, blank=True, verbose_name="LinkedIn username"
    )
    homepage_avatar = ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=SET_NULL,
        related_name="+",
        help_text="An avatar image to appear on the homepage",
    )
    goatcounter_hostname = CharField(
        max_length=64,
        blank=True,
        verbose_name="GoatCounter hostname",
        help_text=(
            "If you are tracking metrics via GoatCounter, this should be just the "
            "hostname section of the URL - e.g. goatcounter.example.com"
        ),
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("lastfm_username"),
                FieldPanel("github_username"),
                FieldPanel("linkedin_username"),
            ],
            heading="Usernames",
            icon="user",
        ),
        FieldPanel("homepage_avatar"),
        MultiFieldPanel(
            [FieldPanel("goatcounter_hostname")], heading="Metrics", icon="thumbtack"
        ),
    ]

    class Meta:
        verbose_name = "Social"

    @cached_property
    def site_copy(self):
        return SiteCopy.objects.filter(locale=Locale.get_active()).first()
