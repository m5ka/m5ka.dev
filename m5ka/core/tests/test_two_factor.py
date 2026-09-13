from io import StringIO
from unittest import mock

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from m5ka.core.models import User
from m5ka.core.tests.utils import create_page

VERIFY_URL = "/admin/2fa/"


def token_for(device):
    return f"{totp(device.bin_key, device.step, device.t0, device.digits):06}"


def create_device(user, name="phone", confirmed=True):
    return TOTPDevice.objects.create(user=user, name=name, confirmed=confirmed)


def verify(client, device, token, **data):
    return client.post(
        VERIFY_URL, {"otp_device": device.persistent_id, "otp_token": token, **data}
    )


@pytest.fixture(autouse=True)
def require_2fa(settings):
    settings.REQUIRE_2FA = True


@pytest.fixture
def device(admin_user):
    return create_device(admin_user)


@pytest.mark.django_db
class TestRequireTwoFactorMiddleware:
    def test_unverified_admin_is_sent_to_verify(self, admin_client, device):
        response = admin_client.get("/admin/pages/")

        assert response.status_code == 302
        assert response.url == f"{VERIFY_URL}?next=/admin/pages/"

    @pytest.mark.parametrize(
        "url", ["/admin/", "/admin/users/", "/admin/settings/m5ka_core/socialsettings/"]
    )
    def test_unverified_admin_cannot_reach_admin_views(self, admin_client, device, url):
        assert admin_client.get(url).status_code == 302

    def test_unverified_admin_cannot_reach_other_views(
        self, admin_client, device, home
    ):
        page = create_page(home, "About")

        assert admin_client.get(page.url).status_code == 302
        assert admin_client.get("/documents/1/doc.pdf").status_code == 302

    def test_unverified_admin_can_sign_out(self, admin_client, device):
        response = admin_client.post(reverse("wagtailadmin_logout"))

        assert response.status_code == 302
        assert "_auth_user_id" not in admin_client.session

    def test_verification_page_assets_load(self, admin_client, device):
        assert admin_client.get(reverse("wagtailadmin_sprite")).status_code == 200
        catalog = reverse("wagtailadmin_javascript_catalog")
        assert admin_client.get(catalog).status_code == 200

    def test_anonymous_visitors_are_unaffected(self, client, home):
        page = create_page(home, "About")

        assert client.get(page.url).status_code == 200
        assert client.get("/admin/").url.startswith("/admin/login/")

    def test_non_admin_users_are_unaffected(self, client, home):
        user = User.objects.create_user(username="reader", password="hunter2hunter2")
        page = create_page(home, "About")
        client.force_login(user)

        assert client.get(page.url).status_code == 200

    def test_not_required_when_disabled(self, admin_client, device, settings):
        settings.REQUIRE_2FA = False

        assert admin_client.get("/admin/").status_code == 200


@pytest.mark.django_db
class TestVerifyTwoFactorView:
    def test_requires_login(self, client):
        response = client.get(VERIFY_URL)

        assert response.status_code == 302
        assert response.url.startswith(reverse("wagtailadmin_login"))

    def test_renders_form_with_hidden_single_device(self, admin_client, device):
        response = admin_client.get(VERIFY_URL)

        content = response.content.decode()
        assert response.status_code == 200
        assert 'name="otp_token"' in content
        assert f'type="hidden" name="otp_device" value="{device.persistent_id}"' in (
            content
        )

    def test_offers_a_choice_of_several_devices(self, admin_client, admin_user):
        create_device(admin_user, "phone")
        create_device(admin_user, "tablet")

        content = admin_client.get(VERIFY_URL).content.decode()

        assert '<select name="otp_device"' in content
        assert "phone" in content and "tablet" in content

    def test_explains_when_no_device_is_set_up(self, admin_client):
        content = admin_client.get(VERIFY_URL).content.decode()

        assert "setup_2fa" in content
        assert 'name="otp_token"' not in content

    def test_valid_code_verifies_the_session(self, admin_client, device):
        response = verify(admin_client, device, token_for(device))

        assert response.status_code == 302
        assert response.url == reverse("wagtailadmin_home")
        assert admin_client.get("/admin/").status_code == 200

    def test_verifying_rotates_the_session_key(self, admin_client, device):
        session_key = admin_client.session.session_key

        verify(admin_client, device, token_for(device))

        assert admin_client.session.session_key != session_key

    def test_redirects_to_next(self, admin_client, device):
        response = verify(admin_client, device, token_for(device), next="/admin/pages/")

        assert response.url == "/admin/pages/"

    def test_does_not_redirect_off_site(self, admin_client, device):
        response = verify(
            admin_client, device, token_for(device), next="https://evil.example.com/"
        )

        assert response.url == reverse("wagtailadmin_home")

    def test_verified_user_is_redirected_away(self, admin_client, device):
        verify(admin_client, device, token_for(device))

        response = admin_client.get(VERIFY_URL)

        assert response.status_code == 302

    def test_wrong_code_is_rejected(self, admin_client, device):
        response = verify(admin_client, device, "000000")

        assert response.status_code == 200
        assert admin_client.get("/admin/").status_code == 302

    def test_missing_code_is_rejected(self, admin_client, device):
        response = verify(admin_client, device, "")

        assert response.status_code == 200
        assert admin_client.get("/admin/").status_code == 302

    def test_another_users_device_is_rejected(self, admin_client, device):
        other = User.objects.create_user(username="other", password="hunter2hunter2")
        other_device = create_device(other)

        response = verify(admin_client, other_device, token_for(other_device))

        assert response.status_code == 200
        assert admin_client.get("/admin/").status_code == 302

    def test_unconfirmed_device_is_rejected(self, admin_client, admin_user, device):
        unconfirmed = create_device(admin_user, "stolen", confirmed=False)

        response = verify(admin_client, unconfirmed, token_for(unconfirmed))

        assert response.status_code == 200
        assert admin_client.get("/admin/").status_code == 302

    def test_failed_codes_throttle_further_attempts(self, admin_client, device):
        verify(admin_client, device, "000000")

        # the right code is still refused while the device is throttled
        response = verify(admin_client, device, token_for(device))

        assert response.status_code == 200
        device.refresh_from_db()
        assert device.throttling_failure_count == 1
        assert admin_client.get("/admin/").status_code == 302

    def test_code_cannot_be_reused(self, admin_client, client, admin_user, device):
        token = token_for(device)
        verify(admin_client, device, token)
        client.force_login(admin_user)

        response = verify(client, device, token)

        assert response.status_code == 200

    def test_code_is_not_exposed_in_error_reports(self, admin_client, device):
        response = verify(admin_client, device, "000000")

        assert response.wsgi_request.sensitive_post_parameters == "__ALL__"


@pytest.mark.django_db
class TestSetupTwoFactorCommand:
    def run(self, *args, code=None):
        stdout = StringIO()
        with mock.patch("builtins.input") as prompt:
            prompt.side_effect = lambda _: code(TOTPDevice.objects.get(confirmed=False))
            call_command("setup_2fa", *args, stdout=stdout)
        return stdout.getvalue()

    def test_confirms_device_with_valid_code(self, admin_user):
        output = self.run("admin", code=token_for)

        device = TOTPDevice.objects.get(user=admin_user)
        assert device.confirmed
        assert device.config_url in output
        assert "issuer=m5ka.dev" in device.config_url

    def test_names_device(self, admin_user):
        self.run("admin", "--name", "Work phone", code=token_for)

        assert TOTPDevice.objects.get(user=admin_user).name == "Work phone"

    def test_wrong_code_leaves_no_device(self, admin_user):
        with pytest.raises(CommandError):
            self.run("admin", code=lambda device: "000000")

        assert not TOTPDevice.objects.filter(user=admin_user).exists()

    def test_keeps_existing_devices(self, admin_user):
        existing = create_device(admin_user, "old phone")

        self.run("admin", code=token_for)

        assert TOTPDevice.objects.filter(user=admin_user, confirmed=True).count() == 2
        assert TOTPDevice.objects.filter(pk=existing.pk).exists()

    def test_replace_removes_other_devices(self, admin_user):
        existing = create_device(admin_user, "lost phone")

        self.run("admin", "--replace", code=token_for)

        assert not TOTPDevice.objects.filter(pk=existing.pk).exists()
        assert TOTPDevice.objects.get(user=admin_user).confirmed

    def test_replace_keeps_devices_when_code_is_wrong(self, admin_user):
        existing = create_device(admin_user, "phone")

        with pytest.raises(CommandError):
            self.run("admin", "--replace", code=lambda device: "000000")

        assert list(TOTPDevice.objects.filter(user=admin_user)) == [existing]

    def test_clears_unconfirmed_devices_from_earlier_runs(self, admin_user):
        create_device(admin_user, "abandoned", confirmed=False)

        self.run("admin", code=token_for)

        assert not TOTPDevice.objects.filter(user=admin_user, name="abandoned").exists()

    def test_unknown_user(self, db):
        with pytest.raises(CommandError, match="nobody"):
            call_command("setup_2fa", "nobody")

    def test_set_up_device_can_verify(self, admin_client, admin_user):
        self.run("admin", code=token_for)
        device = TOTPDevice.objects.get(user=admin_user)
        # a code from the next time step, as the one used for setup can't be reused
        token = f"{totp(device.bin_key, device.step, device.t0 - device.step):06}"

        response = verify(admin_client, device, token)

        assert response.status_code == 302
