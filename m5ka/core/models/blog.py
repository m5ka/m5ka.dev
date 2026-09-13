from django.db.models import SET_NULL, ForeignKey
from django.utils.functional import cached_property
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page

from m5ka.core.blocks import M5kaBlocks


class BlogPost(Page):
    body = StreamField(M5kaBlocks(), blank=True)
    headline_image = ForeignKey(
        "wagtailimages.Image",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    content_panels = Page.content_panels + [
        FieldPanel("headline_image"),
        FieldPanel("body"),
    ]

    parent_page_types = ["m5ka_core.BlogRoot"]
    subpage_types = []


class BlogRoot(Page):
    parent_page_types = ["m5ka_home.HomePage"]
    subpage_types = ["m5ka_core.BlogPost"]
    max_count = 1

    @cached_property
    def posts(self):
        return BlogPost.objects.live().child_of(self)
