from wagtail.fields import StreamField
from wagtail.models import Page

from m5ka.core.blocks import M5kaBlocks


class BlogRoot(Page):
    parent_page_types = ["m5ka_home.HomePage"]
    subpage_types = ["m5ka_core.BlogPost"]
    max_count = 1


class BlogPost(Page):
    body = StreamField(M5kaBlocks(), blank=True)

    parent_page_types = ["m5ka_core.BlogRoot"]
    subpage_types = []
