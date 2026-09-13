import json
import logging
import threading
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import RedirectURLMixin
from django.core.cache import cache
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET
from django.views.generic import FormView
from django_otp import login as otp_login

from m5ka.core.forms import VerifyTwoFactorForm
from m5ka.core.models import SocialSettings

logger = logging.getLogger(__name__)

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
LASTFM_TIMEOUT = 5
NOW_PLAYING_CACHE_SECONDS = 60

# Stops concurrent requests in one worker from all hitting Last.fm on a cache miss.
_now_playing_lock = threading.Lock()


def fetch_now_playing(username):
    query = urlencode(
        {
            "method": "user.getrecenttracks",
            "user": username,
            "limit": 1,
            "api_key": settings.LASTFM_API_KEY,
            "format": "json",
        }
    )
    with urlopen(f"{LASTFM_API_URL}?{query}", timeout=LASTFM_TIMEOUT) as response:
        body = json.load(response)

    tracks = body["recenttracks"]["track"]
    track = tracks[0] if isinstance(tracks, list) else tracks
    return {
        "track": track["name"],
        "playing": track.get("@attr", {}).get("nowplaying") == "true",
    }


def get_now_playing(username):
    """
    Returns the user's latest track, hitting Last.fm at most once per cache period.
    Failures are cached too, so an outage doesn't turn every visit into a request.
    """
    cache_key = f"lastfm:now-playing:{quote(username)}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    with _now_playing_lock:
        data = cache.get(cache_key)
        if data is None:
            try:
                data = fetch_now_playing(username)
            except (OSError, ValueError, LookupError, TypeError):
                logger.warning("Couldn't fetch now playing from Last.fm", exc_info=True)
                data = {"error": True}
            cache.set(cache_key, data, NOW_PLAYING_CACHE_SECONDS)
    return data


@require_GET
def now_playing(request):
    username = SocialSettings.load(request_or_site=request).lastfm_username
    if not username or not settings.LASTFM_API_KEY:
        raise Http404

    data = get_now_playing(username)
    if data.get("error"):
        return JsonResponse({"error": "Last.fm is unavailable"}, status=502)
    return JsonResponse(data)


@method_decorator([sensitive_post_parameters(), never_cache], name="dispatch")
class VerifyTwoFactorView(LoginRequiredMixin, RedirectURLMixin, FormView):
    form_class = VerifyTwoFactorForm
    template_name = "m5ka_core/verify_2fa.html"
    login_url = reverse_lazy("wagtailadmin_login")
    next_page = reverse_lazy("wagtailadmin_home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_verified():
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "next": self.get_redirect_url()}

    def form_valid(self, form):
        # a new session key, as the session has just gained access to the admin
        self.request.session.cycle_key()
        otp_login(self.request, form.get_user().otp_device)
        return super().form_valid(form)
