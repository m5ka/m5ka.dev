import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template import Context, Template
from django.utils import translation
from wagtail.models import Page

from m5ka.core.models import Menu
from m5ka.core.tests.utils import create_menu, publish_translation


@pytest.fixture
def cv(root):
    return root.add_child(instance=Page(title="Curriculum vitae", slug="cv"))


@pytest.fixture
def blog(root):
    return root.add_child(instance=Page(title="Blog", slug="blog"))


def texts(links):
    return [link.text for link in links]


@pytest.mark.django_db
class TestMenuLinks:
    def test_rejects_unknown_handle(self):
        with pytest.raises(ValueError):
            Menu.get_links("sidebar")

    def test_missing_menu_has_no_links(self):
        assert Menu.get_links("header") == []

    def test_label_overrides_page_title(self, en, cv, blog):
        create_menu("header", en, (cv, "CV"), (blog, ""))

        assert texts(Menu.get_links("header")) == ["CV", "Blog"]

    def test_excludes_unpublished_pages(self, en, cv, blog):
        blog.unpublish()
        create_menu("header", en, (cv, ""), (blog, ""))

        assert texts(Menu.get_links("header")) == ["Curriculum vitae"]

    def test_uses_active_locale_menu(self, en, pl, cv):
        create_menu("header", en, (cv, "CV"))
        create_menu("header", pl, (cv, "Życiorys"))

        with translation.override("pl"):
            assert texts(Menu.get_links("header")) == ["Życiorys"]

    def test_falls_back_to_default_locale_menu(self, en, pl, cv):
        create_menu("header", en, (cv, "CV"))

        with translation.override("pl"):
            assert texts(Menu.get_links("header")) == ["CV"]

    def test_swaps_pages_for_live_translations(self, en, pl, cv, blog):
        cv_pl = publish_translation(cv, pl, "Curriculum vitae (pl)")
        create_menu("header", en, (cv, ""), (blog, ""))

        with translation.override("pl"):
            links = Menu.get_links("header")

        assert [link.page.pk for link in links] == [cv_pl.pk, blog.pk]
        assert texts(links) == ["Curriculum vitae (pl)", "Blog"]

    def test_query_count(self, en, pl, cv, blog, django_assert_num_queries):
        publish_translation(cv, pl, "Curriculum vitae (pl)")
        create_menu("header", en, (cv, ""), (blog, ""))

        with django_assert_num_queries(2):
            Menu.get_links("header")
        with translation.override("pl"), django_assert_num_queries(3):
            Menu.get_links("header")


@pytest.mark.django_db
def test_header_renders_menu_links(client, en, home, cv):
    create_menu("header", en, (cv, "CV"), (home, ""))

    response = client.get(home.url)

    assert response.status_code == 200
    assert (
        f'<a class="header__nav-item" href="{cv.url}">CV</a>'
        in response.content.decode()
    )


@pytest.mark.django_db
def test_menu_links_template_tag(en, cv, blog):
    create_menu("footer", en, (cv, "CV"), (blog, ""))
    template = Template(
        "{% load m5ka_navigation %}{% menu_links 'footer' as links %}"
        "{% for link in links %}{{ link.text }};{% endfor %}"
    )

    assert template.render(Context()) == "CV;Blog;"


@pytest.mark.django_db
def test_menu_str(en):
    assert str(create_menu("hamburger", en)) == f"Hamburger ({en})"


@pytest.mark.django_db
def test_menu_snippet_add_view(admin_client):
    response = admin_client.get("/admin/snippets/m5ka_core/menu/add/")

    assert response.status_code == 200


@pytest.mark.django_db
class TestMenuValidation:
    def test_rejects_duplicate_handle_in_locale(self, en):
        create_menu("header", en)

        with pytest.raises(ValidationError) as error:
            Menu(handle="header", locale=en).full_clean()
        assert "handle" in error.value.message_dict

    def test_allows_same_handle_in_other_locale(self, en, pl):
        create_menu("header", en)

        Menu(handle="header", locale=pl).full_clean()

    def test_rejects_unknown_handle(self, en):
        with pytest.raises(ValidationError) as error:
            Menu(handle="sidebar", locale=en).full_clean()
        assert "handle" in error.value.message_dict


@pytest.mark.django_db(transaction=True)
def test_navigation_settings_migrate_to_menus(en, cv, blog):
    before = [("m5ka_core", "0004_menu_menuitem")]
    after = [("m5ka_core", "0006_delete_navigationsettings")]

    executor = MigrationExecutor(connection)
    executor.migrate(before)
    apps = executor.loader.project_state(before).apps
    # unapplying 0005 leaves behind an empty settings row
    apps.get_model("m5ka_core", "NavigationSettings").objects.update(
        header_links=[
            {"type": "page", "value": blog.pk, "id": "a"},
            {"type": "page", "value": 999_999, "id": "b"},
            {"type": "page", "value": cv.pk, "id": "c"},
        ]
    )

    executor.loader.build_graph()
    executor.migrate(after)
    apps = executor.loader.project_state(after).apps
    menus = apps.get_model("m5ka_core", "Menu").objects.all()

    assert [menu.handle for menu in menus] == ["header"]
    assert menus[0].locale_id == en.pk
    assert list(
        menus[0].items.order_by("sort_order").values_list("page_id", flat=True)
    ) == [blog.pk, cv.pk]

    executor.loader.build_graph()
    executor.migrate(before)
    apps = executor.loader.project_state(before).apps
    navigation = apps.get_model("m5ka_core", "NavigationSettings").objects.get()
    assert [block["value"] for block in navigation.header_links.raw_data] == [
        blog.pk,
        cv.pk,
    ]

    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
