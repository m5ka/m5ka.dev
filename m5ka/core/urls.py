from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from m5ka.core import views as core_views
from m5ka.search import views as search_views

urlpatterns = [
    path("admin/2fa/", core_views.VerifyTwoFactorView.as_view(), name="verify_2fa"),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("api/now-playing/", core_views.now_playing, name="now_playing"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Make django-admin public only in dev environment
    urlpatterns += [path("django-admin/", admin.site.urls)]

    # Serve static files only in dev environment
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


urlpatterns = urlpatterns + i18n_patterns(
    path("search/", search_views.search, name="search"),
    path("", include(wagtail_urls)),
    prefix_default_language=False,
)
