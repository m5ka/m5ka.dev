import re

import pytest
from django.template.loader import render_to_string
from django.utils import translation
from pytest_django.asserts import assertTemplateUsed
from wagtail.models import Site

from m5ka.core.tests.utils import create_page, publish_translation


def get_title(response):
    title = re.search(r"<title>(.*?)</title>", response.content.decode(), re.DOTALL)
    return " ".join(title[1].split())


@pytest.mark.django_db
class TestContentPageView:
    def test_renders_title_and_body(self, client, home):
        page = create_page(
            home,
            "About",
            body=[
                ("heading", "Who am I?"),
                ("paragraph", "<p>Just some person</p>"),
                ("divider", None),
            ],
        )

        response = client.get(page.url)

        assert response.status_code == 200
        assertTemplateUsed(response, "m5ka_core/page.html")
        content = response.content.decode()
        assert '<h2 class="main__title">About</h2>' in content
        assert f'<h3 class="heading" id="{page.body[0].id}">Who am I?</h3>' in content
        assert "Just some person" in content
        assert '<hr class="divider" />' in content

    def test_renders_nested_page(self, client, home):
        parent = create_page(home, "Projects")
        child = create_page(parent, "Website")

        response = client.get(child.url)

        assert child.url == "/projects/website/"
        assert response.status_code == 200

    def test_renders_empty_body(self, client, home):
        page = create_page(home, "Empty")

        response = client.get(page.url)

        assert response.status_code == 200

    def test_unpublished_page_is_not_found(self, client, home):
        page = create_page(home, "Secret", live=False)

        response = client.get(page.get_url())

        assert response.status_code == 404


@pytest.mark.django_db
class TestBaseTemplate:
    def test_title_uses_page_title(self, client, home):
        page = create_page(home, "About")

        assert get_title(client.get(page.url)) == "About"

    def test_title_prefers_seo_title(self, client, home):
        page = create_page(home, "About", seo_title="About me, in detail")

        assert get_title(client.get(page.url)) == "About me, in detail"

    def test_title_is_suffixed_with_site_name(self, client, home):
        Site.objects.update(site_name="m5ka.dev")
        page = create_page(home, "About")

        assert get_title(client.get(page.url)) == "About - m5ka.dev"

    def test_home_page_title_is_only_site_name(self, client, home):
        Site.objects.update(site_name="m5ka.dev")

        assert get_title(client.get(home.url)) == "m5ka.dev"

    def test_renders_meta_description(self, client, home):
        page = create_page(home, "About", search_description="All about me")

        response = client.get(page.url)

        assert (
            '<meta name="description" content="All about me" />'
            in response.content.decode()
        )

    def test_omits_empty_meta_description(self, client, home):
        page = create_page(home, "About")

        response = client.get(page.url)

        assert 'name="description"' not in response.content.decode()

    def test_brand_links_to_home(self, client, home):
        page = create_page(home, "About")

        response = client.get(page.url)

        assert (
            f'<a href="{home.url}" class="header__brand">' in response.content.decode()
        )

    def test_renders_default_language(self, client, home):
        response = client.get(home.url)

        assert '<html lang="en">' in response.content.decode()


@pytest.mark.django_db
class TestTranslations:
    def test_translated_page_is_served_under_language_prefix(self, client, pl, home):
        page = create_page(home, "About")
        page_pl = publish_translation(page, pl, "O mnie", copy_parents=True)

        response = client.get(page_pl.url)

        assert page_pl.url == "/pl/about/"
        assert response.status_code == 200
        content = response.content.decode()
        assert '<html lang="pl">' in content
        assert '<h2 class="main__title">O mnie</h2>' in content

    def test_default_language_is_not_prefixed(self, client, pl, home):
        page = create_page(home, "About")
        publish_translation(page, pl, "O mnie", copy_parents=True)

        response = client.get("/about/")

        assert response.status_code == 200
        assert '<h2 class="main__title">About</h2>' in response.content.decode()

    def test_header_links_to_live_translations(self, client, pl, home):
        page = create_page(home, "About")
        page_pl = publish_translation(page, pl, "O mnie", copy_parents=True)

        response = client.get(page.url)

        content = response.content.decode()
        assert (
            f'<a class="header__translation" href="{page_pl.url}" rel="alternate" '
            'hreflang="pl">' in content
        )
        assert "polski" in content

    def test_header_omits_draft_translations(self, client, pl, home):
        page = create_page(home, "About")
        page_pl = publish_translation(page, pl, "O mnie", copy_parents=True)
        page_pl.unpublish()

        response = client.get(page.url)

        assert 'hreflang="pl"' not in response.content.decode()

    def test_brand_links_to_localized_home(self, client, pl, home):
        page = create_page(home, "About")
        page_pl = publish_translation(page, pl, "O mnie", copy_parents=True)

        response = client.get(page_pl.url)

        with translation.override("pl"):
            home_pl_url = home.localized.url
        assert home_pl_url == "/pl/"
        assert (
            f'<a href="{home_pl_url}" class="header__brand">'
            in response.content.decode()
        )


@pytest.mark.django_db
class TestErrorPages:
    def test_not_found_renders_custom_template(self, client, home):
        response = client.get("/this-page-does-not-exist/")

        assert response.status_code == 404
        assertTemplateUsed(response, "404.html")
        assert "Sorryyyyyyyy! That page doesn't exist." in response.content.decode()

    def test_not_found_has_no_translation_links(self, client, home):
        response = client.get("/this-page-does-not-exist/")

        assert "header__translation" not in response.content.decode()

    def test_server_error_template_is_standalone(self):
        html = render_to_string("500.html")

        assert "<h1>Internal server error</h1>" in html
