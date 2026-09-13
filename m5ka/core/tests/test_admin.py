import importlib
from io import StringIO

import pytest
from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import clear_url_caches
from wagtail.models import Page
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from m5ka.core import urls
from m5ka.core.models import BlogPost, User


@pytest.fixture
def urlconf(settings):
    """
    The URLconf checks DEBUG at import time, so it's reloaded to pick up a change.
    """
    original_debug = settings.DEBUG

    def reload(debug):
        settings.DEBUG = debug
        importlib.reload(urls)
        clear_url_caches()

    yield reload
    reload(original_debug)


def test_custom_user_model_is_active():
    assert get_user_model() is User


@pytest.mark.django_db
class TestUser:
    def test_create_user(self):
        user = User.objects.create_user(username="m5ka", password="hunter2hunter2")

        assert user.check_password("hunter2hunter2")
        assert not user.is_staff
        assert not user.is_superuser

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            username="admin", password="hunter2hunter2"
        )

        assert user.is_staff
        assert user.is_superuser

    def test_passwords_shorter_than_12_characters_are_rejected(self):
        with pytest.raises(ValidationError):
            validate_password("xK9#mQ2$vL7")

    def test_passwords_of_12_characters_are_accepted(self):
        validate_password("xK9#mQ2$vL7&")


@pytest.mark.django_db
class TestAdminAccess:
    def test_wagtail_admin_requires_login(self, client):
        response = client.get("/admin/")

        assert response.status_code == 302
        assert response.url.startswith("/admin/login/")

    def test_wagtail_admin_dashboard(self, admin_client):
        assert admin_client.get("/admin/").status_code == 200

    def test_django_admin_is_available_in_debug(self, admin_client, urlconf):
        urlconf(debug=True)

        assert admin_client.get("/django-admin/").status_code == 200

    def test_django_admin_is_not_available_in_production(self, admin_client, urlconf):
        urlconf(debug=False)

        assert admin_client.get("/django-admin/").status_code == 404


@pytest.mark.django_db
class TestAdminEditViews:
    """
    Loading the create and edit views exercises each model's panel configuration,
    which is otherwise only checked when an editor opens them.
    """

    @pytest.mark.parametrize(
        ("app_label", "model", "parent"),
        [("m5ka_core", "page", "home"), ("m5ka_core", "blogroot", "home")],
    )
    def test_page_add_views(self, admin_client, request, app_label, model, parent):
        parent_page = request.getfixturevalue(parent)

        response = admin_client.get(
            f"/admin/pages/add/{app_label}/{model}/{parent_page.pk}/"
        )

        assert response.status_code == 200

    def test_blog_post_add_view(self, admin_client, blog_root):
        response = admin_client.get(
            f"/admin/pages/add/m5ka_core/blogpost/{blog_root.pk}/"
        )

        assert response.status_code == 200

    def test_page_edit_views(self, admin_client, home, blog_root):
        for page in Page.objects.filter(depth__gt=1):
            response = admin_client.get(f"/admin/pages/{page.pk}/edit/")

            assert response.status_code == 200, page

    def test_social_settings_edit_view(self, admin_client):
        response = admin_client.get(
            "/admin/settings/m5ka_core/socialsettings/", follow=True
        )

        assert response.status_code == 200

    @pytest.mark.parametrize("model", ["sitecopy", "menu"])
    def test_snippet_add_views(self, admin_client, model):
        response = admin_client.get(f"/admin/snippets/m5ka_core/{model}/add/")

        assert response.status_code == 200


@pytest.mark.django_db
def test_publish_blog_post_through_admin(admin_client, client, blog_root):
    response = admin_client.post(
        f"/admin/pages/add/m5ka_core/blogpost/{blog_root.pk}/",
        nested_form_data(
            {
                "title": "Written in the admin",
                "slug": "written-in-the-admin",
                "body": streamfield(
                    [
                        ("heading", "A heading"),
                        ("paragraph", rich_text("<p>Some prose</p>")),
                    ]
                ),
                "action-publish": "publish",
            }
        ),
    )

    assert response.status_code == 302
    post = BlogPost.objects.get(slug="written-in-the-admin")
    assert post.live
    assert [block.block_type for block in post.body] == ["heading", "paragraph"]
    assert "Written in the admin" in client.get(blog_root.url).content.decode()


@pytest.mark.django_db
class TestLoginRateLimiting:
    def failed_login(self, client):
        return client.post(
            "/admin/login/", {"username": "admin", "password": "wrong-password"}
        )

    def test_wagtail_login_locks_out_after_failure_limit(self, client, settings):
        User.objects.create_superuser(username="admin", password="hunter2hunter2")

        for _ in range(settings.AXES_FAILURE_LIMIT - 1):
            assert self.failed_login(client).status_code == 200

        assert self.failed_login(client).status_code == 429
        assert AccessAttempt.objects.filter(username="admin").exists()

    def test_lockout_can_be_lifted_with_axes_reset(self, client, settings):
        User.objects.create_superuser(username="admin", password="hunter2hunter2")
        for _ in range(settings.AXES_FAILURE_LIMIT):
            self.failed_login(client)

        call_command("axes_reset_username", "admin", stdout=StringIO())

        response = client.post(
            "/admin/login/", {"username": "admin", "password": "hunter2hunter2"}
        )
        assert response.status_code == 302
        assert not AccessAttempt.objects.exists()
