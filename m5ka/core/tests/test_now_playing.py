import io
import json
from unittest import mock
from urllib.parse import parse_qs, urlparse

import pytest
from django.core.cache import cache

from m5ka.core.models import SocialSettings

URL = "/api/now-playing/"


def lastfm_body(name="Song", nowplaying=False):
    track = {"name": name}
    if nowplaying:
        track["@attr"] = {"nowplaying": "true"}
    return io.BytesIO(json.dumps({"recenttracks": {"track": [track]}}).encode())


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def lastfm_settings(settings):
    settings.LASTFM_API_KEY = "secret-key"
    return SocialSettings.objects.create(lastfm_username="fm user")


@pytest.fixture
def urlopen():
    with mock.patch("m5ka.core.views.urlopen") as urlopen:
        yield urlopen


@pytest.mark.django_db
class TestNowPlaying:
    def test_returns_current_track(self, client, lastfm_settings, urlopen):
        urlopen.return_value.__enter__.return_value = lastfm_body("Hey", True)

        response = client.get(URL)

        assert response.status_code == 200
        assert response.json() == {"track": "Hey", "playing": True}

    def test_returns_last_track_when_not_playing(
        self, client, lastfm_settings, urlopen
    ):
        urlopen.return_value.__enter__.return_value = lastfm_body("Old", False)

        response = client.get(URL)

        assert response.json() == {"track": "Old", "playing": False}

    def test_queries_lastfm_with_server_side_key(
        self, client, lastfm_settings, urlopen
    ):
        urlopen.return_value.__enter__.return_value = lastfm_body()

        client.get(URL)

        query = parse_qs(urlparse(urlopen.call_args.args[0]).query)
        assert query["user"] == ["fm user"]
        assert query["api_key"] == ["secret-key"]

    def test_does_not_expose_key(self, client, lastfm_settings, urlopen):
        urlopen.return_value.__enter__.return_value = lastfm_body()

        response = client.get(URL)

        assert "secret-key" not in response.content.decode()

    def test_caches_lastfm_response(self, client, lastfm_settings, urlopen):
        urlopen.return_value.__enter__.side_effect = [lastfm_body("First")]

        client.get(URL)
        response = client.get(URL)

        assert urlopen.call_count == 1
        assert response.json()["track"] == "First"

    def test_returns_502_and_caches_failure(self, client, lastfm_settings, urlopen):
        urlopen.side_effect = OSError("boom")

        first = client.get(URL)
        second = client.get(URL)

        assert first.status_code == second.status_code == 502
        assert urlopen.call_count == 1

    def test_returns_502_on_unexpected_body(self, client, lastfm_settings, urlopen):
        urlopen.return_value.__enter__.return_value = io.BytesIO(b'{"error": 6}')

        response = client.get(URL)

        assert response.status_code == 502

    def test_404_without_username(self, client, settings, urlopen):
        settings.LASTFM_API_KEY = "secret-key"
        SocialSettings.objects.create()

        response = client.get(URL)

        assert response.status_code == 404
        urlopen.assert_not_called()

    def test_404_without_api_key(self, client, lastfm_settings, settings, urlopen):
        settings.LASTFM_API_KEY = ""

        response = client.get(URL)

        assert response.status_code == 404
        urlopen.assert_not_called()

    def test_rejects_post(self, client, lastfm_settings, urlopen):
        response = client.post(URL)

        assert response.status_code == 405
