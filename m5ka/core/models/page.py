from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page as WagtailPage

from m5ka.core.blocks import M5kaBlocks


class Page(WagtailPage):
    body = StreamField(M5kaBlocks(), blank=True)

    parent_page_types = ["m5ka_core.Page", "m5ka_home.HomePage"]
    subpage_types = ["m5ka_core.Page"]

    content_panels = WagtailPage.content_panels + [FieldPanel("body", icon="pilcrow")]
