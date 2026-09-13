import importlib
import sys

import pytest
from django.utils.csp import CSP
from environs import EnvValidationError

PRODUCTION = "m5ka.settings.production"
S3_ENDPOINT = "https://s3.example.com"
REQUIRED_ENV = {
    "S3_BUCKET_NAME_MEDIA": "media",
    "S3_BUCKET_NAME_STATIC": "static",
    "S3_ENDPOINT_URL": S3_ENDPOINT,
    "S3_ACCESS_KEY": "access",
    "S3_SECRET_KEY": "secret",
}


@pytest.fixture
def production(monkeypatch):
    """
    Imports a fresh copy of the production settings module under the given env vars.
    It's only inspected, never activated, so the test run keeps the dev settings.
    """

    def load(**env):
        monkeypatch.delenv("M5KA_GOATCOUNTER_URL", raising=False)
        for name, value in {**REQUIRED_ENV, **env}.items():
            monkeypatch.setenv(f"M5KA_{name}", value)
        sys.modules.pop(PRODUCTION, None)
        return importlib.import_module(PRODUCTION)

    yield load
    sys.modules.pop(PRODUCTION, None)


@pytest.fixture
def csp_client(client, settings):
    def configure(production_settings):
        settings.MIDDLEWARE = production_settings.MIDDLEWARE
        settings.SECURE_CSP_REPORT_ONLY = production_settings.SECURE_CSP_REPORT_ONLY
        settings.GOATCOUNTER_URL = production_settings.GOATCOUNTER_URL
        return client

    return configure


class TestProductionSettings:
    def test_debug_is_off(self, production):
        assert production().DEBUG is False

    def test_https_is_enforced(self, production):
        settings = production()

        assert settings.SECURE_SSL_REDIRECT is True
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SECURE is True
        assert settings.SECURE_HSTS_SECONDS > 0
        assert settings.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")

    def test_two_factor_auth_is_required(self, production):
        assert production().REQUIRE_2FA is True

    def test_axes_uses_the_ip_address_the_proxy_saw(self, production):
        settings = production()

        assert settings.AXES_IPWARE_META_PRECEDENCE_ORDER[0] == "HTTP_X_FORWARDED_FOR"
        assert settings.AXES_IPWARE_PROXY_ORDER == "right-most"

    def test_csp_middleware_is_enabled(self, production):
        settings = production()

        assert "django.middleware.csp.ContentSecurityPolicyMiddleware" in (
            settings.MIDDLEWARE
        )

    def test_does_not_change_base_middleware(self, production):
        from m5ka.settings import base

        production()

        assert "django.middleware.csp.ContentSecurityPolicyMiddleware" not in (
            base.MIDDLEWARE
        )

    def test_csp_only_allows_first_party_sources(self, production):
        policy = production().SECURE_CSP_REPORT_ONLY

        assert policy["default-src"] == [CSP.SELF]
        assert policy["script-src"] == [CSP.SELF, S3_ENDPOINT]
        assert policy["style-src"] == [CSP.SELF, S3_ENDPOINT]
        assert policy["font-src"] == [CSP.SELF, S3_ENDPOINT]
        assert policy["img-src"] == [CSP.SELF, S3_ENDPOINT]
        assert policy["connect-src"] == [CSP.SELF]
        assert policy["frame-src"] == ["https://www.youtube-nocookie.com"]
        assert policy["frame-ancestors"] == [CSP.NONE]
        assert policy["object-src"] == [CSP.NONE]

    def test_goatcounter_is_off_when_unset(self, production):
        assert production().GOATCOUNTER_URL is None

    def test_goatcounter_is_off_when_empty(self, production):
        # docker-compose.yml passes an empty string when the variable is unset
        assert production(GOATCOUNTER_URL="").GOATCOUNTER_URL is None

    @pytest.mark.parametrize(
        "value",
        [
            "https://stats.example.com",
            "https://stats.example.com/",
            "https://stats.example.com/count",
        ],
    )
    def test_goatcounter_url_is_normalised_to_origin(self, production, value):
        settings = production(GOATCOUNTER_URL=value)

        assert settings.GOATCOUNTER_URL == "https://stats.example.com"

    @pytest.mark.parametrize("value", ["http://stats.example.com", "stats.example.com"])
    def test_goatcounter_url_must_be_https(self, production, value):
        with pytest.raises(EnvValidationError):
            production(GOATCOUNTER_URL=value)

    def test_goatcounter_is_added_to_csp(self, production):
        policy = production(
            GOATCOUNTER_URL="https://stats.example.com"
        ).SECURE_CSP_REPORT_ONLY

        for directive in ("script-src", "connect-src", "img-src"):
            assert "https://stats.example.com" in policy[directive]
        for directive in ("default-src", "style-src", "font-src", "frame-src"):
            assert "https://stats.example.com" not in policy[directive]


@pytest.mark.django_db
class TestContentSecurityPolicyHeader:
    def test_sends_report_only_policy(self, production, csp_client, home):
        client = csp_client(production())

        response = client.get(home.url)

        policy = response.headers["Content-Security-Policy-Report-Only"]
        assert "default-src 'self'" in policy
        assert "frame-ancestors 'none'" in policy
        assert "googleapis" not in policy
        assert "gstatic" not in policy
        assert "audioscrobbler" not in policy

    def test_policy_allows_the_goatcounter_script_it_renders(
        self, production, csp_client, home
    ):
        client = csp_client(production(GOATCOUNTER_URL="https://stats.example.com"))

        response = client.get(home.url)

        policy = response.headers["Content-Security-Policy-Report-Only"]
        assert f"script-src 'self' {S3_ENDPOINT} https://stats.example.com" in policy
        assert 'src="https://stats.example.com/count.js"' in response.content.decode()
