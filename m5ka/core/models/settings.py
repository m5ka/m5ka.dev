from django.db.models import CharField, ForeignKey, SET_NULL, TextField
from wagtail.admin.panels import MultiFieldPanel, FieldPanel
from wagtail.blocks import PageChooserBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting


@register_setting(icon="glasses")
class CustomisationSettings(BaseGenericSetting):
    lastfm_username = CharField(max_length=128, blank=True, verbose_name="LastFM username")
    github_username = CharField(max_length=128, blank=True)
    linkedin_username = CharField(max_length=128, blank=True, verbose_name="LinkedIn username")
    homepage_heading = CharField(max_length=128, blank=True, help_text="A hero heading to appear on the homepage")
    homepage_avatar = ForeignKey("wagtailimages.Image", null=True, blank=True, on_delete=SET_NULL, related_name="+", help_text="An avatar image to appear on the homepage")
    short_bio = TextField(blank=True, help_text="A short bio to appear on the homepage")
    footer_text = RichTextField(features=["bold", "italic", "hr", "link"], blank=True)
    copyright_author = CharField(max_length=64, blank=True)
    goatcounter_hostname = CharField(max_length=64, blank=True, verbose_name="GoatCounter hostname", help_text="If you are tracking metrics via GoatCounter, this should be just the hostname section of the URL - e.g. goatcounter.example.com")

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
        MultiFieldPanel(
            [
                FieldPanel("homepage_heading"),
                FieldPanel("homepage_avatar"),
                FieldPanel("short_bio"),
            ],
            heading="Homepage",
            icon="snippet",
        ),
        MultiFieldPanel(
            [
                FieldPanel("footer_text"),
                FieldPanel("copyright_author"),
            ],
            heading="Footer",
            icon="order-down",
        ),
        MultiFieldPanel(
            [FieldPanel("goatcounter_hostname")],
            heading="Metrics",
            icon="thumbtack",
        )
    ]

    class Meta:
        verbose_name = "Customisation"


@register_setting(icon="link")
class NavigationSettings(BaseGenericSetting):
    header_links = StreamField([("page", PageChooserBlock(icon="doc-empty"))], blank=True)
    hamburger_links = StreamField([("page", PageChooserBlock(icon="doc-empty"))], blank=True)
    footer_links = StreamField([("page", PageChooserBlock(icon="doc-empty"))], blank=True)

    panels = [
        FieldPanel("header_links", icon="title"),
        FieldPanel("hamburger_links", icon="bars"),
        FieldPanel("footer_links", icon="order-down"),
    ]

    class Meta:
        verbose_name = "Navigation"
