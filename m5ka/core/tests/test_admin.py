import pytest
from django.contrib.auth import get_user_model
from wagtail.models import Page
from wagtail.test.utils.form_data import nested_form_data, rich_text, streamfield

from m5ka.core.models import BlogPost, User


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


@pytest.mark.django_db
class TestAdminAccess:
    def test_wagtail_admin_requires_login(self, client):
        response = client.get("/admin/")

        assert response.status_code == 302
        assert response.url.startswith("/admin/login/")

    def test_wagtail_admin_dashboard(self, admin_client):
        assert admin_client.get("/admin/").status_code == 200

    def test_django_admin(self, admin_client):
        assert admin_client.get("/django-admin/").status_code == 200


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
