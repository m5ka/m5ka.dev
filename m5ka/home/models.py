from django.db.models import CharField
from wagtail.admin.panels import FieldPanel
from wagtail.models import Page


class HomePage(Page):
    subpage_types = ["m5ka_core.BlogRoot", "m5ka_core.Page"]
