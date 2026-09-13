from io import StringIO

import pytest
from django.core.management import call_command
from wagtail.models import Site

from m5ka.home.models import HomePage


@pytest.mark.django_db
def test_no_missing_migrations():
    # exits with a non-zero status if any model changes lack a migration
    call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


@pytest.mark.django_db
def test_initial_data_creates_default_site_with_home_page():
    site = Site.objects.get(is_default_site=True)

    assert site.hostname == "localhost"
    assert isinstance(site.root_page.specific, HomePage)
    assert site.root_page.slug == "home"
