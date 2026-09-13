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
def test_removes_wagtail_2fa_permission():
    from importlib import import_module

    from django.apps import apps
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.models import ContentType

    content_type, _ = ContentType.objects.get_or_create(
        app_label="wagtailadmin", model="admin"
    )
    Permission.objects.create(
        content_type=content_type, codename="enable_2fa", name="Enable 2FA"
    )
    migration = import_module("m5ka.core.migrations.0010_remove_wagtail_2fa_permission")

    migration.remove_enable_2fa_permission(apps, None)

    assert not Permission.objects.filter(codename="enable_2fa").exists()
    assert Permission.objects.filter(codename="access_admin").exists()


@pytest.mark.django_db
def test_initial_data_creates_default_site_with_home_page():
    site = Site.objects.get(is_default_site=True)

    assert site.hostname == "localhost"
    assert isinstance(site.root_page.specific, HomePage)
    assert site.root_page.slug == "home"
