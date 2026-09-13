from django.utils.functional import cached_property
from wagtail.models import Page

from m5ka.core.models import BlogPost


class HomePage(Page):
    subpage_types = ["m5ka_core.BlogRoot", "m5ka_core.Page"]

    @cached_property
    def posts(self):
        return BlogPost.objects.live().public().descendant_of(self)
