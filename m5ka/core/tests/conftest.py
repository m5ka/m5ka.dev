import pytest
from django.utils import translation
from wagtail.images import get_image_model
from wagtail.images.tests.utils import get_test_image_file
from wagtail.models import Locale, Page

from m5ka.core.models import BlogRoot
from m5ka.home.models import HomePage


@pytest.fixture(autouse=True)
def static_storage(settings):
    # the manifest storage needs collectstatic to have been run
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture(autouse=True)
def reset_language():
    # requests to localised URLs leave their language active on the thread
    translation.deactivate()
    yield
    translation.deactivate()


@pytest.fixture
def en():
    return Locale.objects.get(language_code="en")


@pytest.fixture
def pl():
    return Locale.objects.create(language_code="pl")


@pytest.fixture
def root():
    return Page.objects.get(depth=1)


@pytest.fixture
def home():
    return HomePage.objects.get()


@pytest.fixture
def blog_root(home):
    return home.add_child(instance=BlogRoot(title="Blog", slug="blog"))


@pytest.fixture
def image():
    return get_image_model().objects.create(
        title="Test image", file=get_test_image_file(size=(640, 480))
    )
