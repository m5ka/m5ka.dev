import pytest
from django.db import IntegrityError
from django.utils import timezone, translation

from m5ka.core.models import SiteCopy, SocialSettings
from m5ka.core.tests.utils import create_site_copy, publish_translation


@pytest.mark.django_db
class TestSiteCopy:
    def test_str_is_locale(self, en):
        assert str(create_site_copy(en)) == str(en)

    def test_one_per_locale(self, en):
        create_site_copy(en)

        with pytest.raises(IntegrityError):
            create_site_copy(en)

    def test_one_per_each_locale(self, en, pl):
        create_site_copy(en)
        create_site_copy(pl)

        assert SiteCopy.objects.count() == 2


@pytest.mark.django_db
class TestSocialSettingsSiteCopy:
    def test_none_when_no_site_copy(self, en):
        assert SocialSettings.load().site_copy is None

    def test_uses_active_locale(self, en, pl):
        create_site_copy(en, homepage_heading="Hello")
        create_site_copy(pl, homepage_heading="Cześć")

        assert SocialSettings.load().site_copy.homepage_heading == "Hello"
        with translation.override("pl"):
            assert SocialSettings.load().site_copy.homepage_heading == "Cześć"

    def test_none_when_active_locale_has_no_site_copy(self, en, pl):
        create_site_copy(en, homepage_heading="Hello")

        with translation.override("pl"):
            assert SocialSettings.load().site_copy is None


@pytest.mark.django_db
class TestFooter:
    def test_renders_footer_text(self, client, en, home):
        create_site_copy(en, footer_text="<p>Made with <b>love</b></p>")

        response = client.get(home.url)

        content = response.content.decode()
        assert '<div class="footer__content">' in content
        assert "Made with <b>love</b>" in content

    def test_renders_copyright(self, client, en, home):
        create_site_copy(en, copyright_author="m5ka")

        response = client.get(home.url)

        year = timezone.now().year
        assert (
            f'<p class="footer__copyright">&copy; {year} m5ka</p>'
            in response.content.decode()
        )

    def test_omits_empty_copy(self, client, en, home):
        create_site_copy(en)

        response = client.get(home.url)

        content = response.content.decode()
        assert "footer__content" not in content
        assert "footer__copyright" not in content

    def test_renders_without_site_copy(self, client, home):
        response = client.get(home.url)

        assert response.status_code == 200
        assert "footer__copyright" not in response.content.decode()

    def test_renders_copy_for_active_locale(self, client, en, pl, home):
        create_site_copy(en, copyright_author="English author")
        create_site_copy(pl, copyright_author="Polish author")
        home_pl = publish_translation(home, pl, "Strona główna")

        response = client.get(home_pl.url)

        content = response.content.decode()
        assert "Polish author" in content
        assert "English author" not in content


@pytest.mark.django_db
class TestHomePageHero:
    def test_renders_heading_and_bio(self, client, en, home):
        create_site_copy(en, homepage_heading="Hi, I'm m5ka", short_bio="I make things")

        response = client.get(home.url)

        content = response.content.decode()
        assert '<h2 class="hero__heading">Hi, I&#x27;m m5ka</h2>' in content
        assert '<div class="hero__subheading">I make things</div>' in content

    def test_omits_empty_heading_and_bio(self, client, en, home):
        create_site_copy(en)

        response = client.get(home.url)

        content = response.content.decode()
        assert "hero__heading" not in content
        assert "hero__subheading" not in content

    def test_renders_social_links(self, client, home):
        SocialSettings.objects.create(
            github_username="gh-user",
            linkedin_username="li-user",
            lastfm_username="fm-user",
        )

        response = client.get(home.url)

        content = response.content.decode()
        assert 'href="https://github.com/gh-user"' in content
        assert 'href="https://linkedin.com/in/li-user"' in content
        assert 'href="https://last.fm/user/fm-user"' in content
        assert 'data-lastfm-username="fm-user"' in content

    def test_omits_unset_social_links(self, client, home):
        SocialSettings.objects.create(github_username="gh-user")

        response = client.get(home.url)

        content = response.content.decode()
        assert 'href="https://github.com/gh-user"' in content
        assert "linkedin.com" not in content
        assert "last.fm" not in content
        assert 'id="nowlistening"' not in content

    def test_renders_avatar(self, client, home, image):
        SocialSettings.objects.create(homepage_avatar=image)

        response = client.get(home.url)

        rendition = image.get_rendition("fill-400x400|format-webp")
        assert f'src="{rendition.url}"' in response.content.decode()

    def test_omits_avatar_when_unset(self, client, home):
        response = client.get(home.url)

        assert "hero__image" not in response.content.decode()

    def test_avatar_is_cleared_when_image_is_deleted(self, image):
        SocialSettings.objects.create(homepage_avatar=image)

        image.delete()

        assert SocialSettings.load().homepage_avatar is None
