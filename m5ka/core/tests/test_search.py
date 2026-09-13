import pytest
from pytest_django.asserts import assertTemplateUsed

from m5ka.core.tests.utils import create_page


def result_titles(response):
    return [result.title for result in response.context["search_results"]]


@pytest.mark.django_db
class TestSearchView:
    def test_renders_empty_form_without_query(self, client):
        response = client.get("/search/")

        assert response.status_code == 200
        assertTemplateUsed(response, "search/search.html")
        assert response.context["search_query"] is None
        assert result_titles(response) == []
        assert "No results found" not in response.content.decode()

    def test_finds_matching_pages(self, client, home):
        create_page(home, "Pineapples")
        create_page(home, "Bananas")

        response = client.get("/search/", {"query": "pineapples"})

        assert result_titles(response) == ["Pineapples"]
        assert "Pineapples" in response.content.decode()

    def test_excludes_unpublished_pages(self, client, home):
        create_page(home, "Secret pineapples", live=False)

        response = client.get("/search/", {"query": "pineapples"})

        assert result_titles(response) == []
        assert "No results found" in response.content.decode()

    def test_renders_search_description(self, client, home):
        create_page(home, "Pineapples", search_description="Spiky and sweet")

        response = client.get("/search/", {"query": "pineapples"})

        assert "Spiky and sweet" in response.content.decode()

    def test_paginates_results(self, client, home):
        for number in range(12):
            create_page(home, f"Pineapple {number}")

        first = client.get("/search/", {"query": "pineapple"})
        second = client.get("/search/", {"query": "pineapple", "page": 2})

        assert len(result_titles(first)) == 10
        assert len(result_titles(second)) == 2
        assert "page=2" in first.content.decode()
        assert "page=1" in second.content.decode()

    def test_invalid_page_falls_back_to_first_page(self, client, home):
        create_page(home, "Pineapples")

        response = client.get("/search/", {"query": "pineapples", "page": "nope"})

        assert response.status_code == 200
        assert response.context["search_results"].number == 1

    def test_out_of_range_page_falls_back_to_last_page(self, client, home):
        for number in range(12):
            create_page(home, f"Pineapple {number}")

        response = client.get("/search/", {"query": "pineapple", "page": 99})

        assert response.status_code == 200
        assert response.context["search_results"].number == 2

    def test_available_under_language_prefix(self, client, pl):
        response = client.get("/pl/search/")

        assert response.status_code == 200
        assert '<html lang="pl">' in response.content.decode()
