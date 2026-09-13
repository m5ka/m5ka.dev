import re

import pytest
from django.contrib.staticfiles import finders

CSS_URL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""")
THIRD_PARTY = ("googleapis", "gstatic", "audioscrobbler", "last.fm/2.0", "zgo.at")


def read_static(path):
    location = finders.find(path)
    assert location, f"{path} is missing from static files"
    with open(location, encoding="utf-8") as file:
        return file.read()


class TestSelfHostedAssets:
    @pytest.mark.parametrize("path", ["css/m5ka.css", "css/fonts.css", "css/reset.css"])
    def test_stylesheets_only_reference_local_files(self, path):
        for url in CSS_URL.findall(read_static(path)):
            assert not re.match(r"^([a-z]+:)?//", url), f"{path} loads {url}"

    def test_font_files_exist(self):
        urls = CSS_URL.findall(read_static("css/fonts.css"))

        assert urls
        for url in urls:
            assert finders.find(f"css/{url}"), f"{url} is missing from static files"

    def test_fonts_are_declared(self):
        css = read_static("css/fonts.css")

        assert "font-family: 'IBM Plex Mono'" in css
        assert "font-family: 'Libre Baskerville'" in css

    @pytest.mark.parametrize("path", ["css/m5ka.css", "css/fonts.css", "js/m5ka.js"])
    def test_does_not_contact_third_parties(self, path):
        content = read_static(path)

        for host in THIRD_PARTY:
            assert host not in content

    def test_script_has_no_api_key(self):
        assert "api_key" not in read_static("js/m5ka.js")

    def test_script_does_not_inject_html(self):
        assert "innerHTML" not in read_static("js/m5ka.js")


@pytest.mark.django_db
def test_pages_load_no_third_party_resources(client, home):
    content = client.get(home.url).content.decode()

    for host in THIRD_PARTY:
        assert host not in content
