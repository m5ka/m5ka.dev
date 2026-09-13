from django.conf import settings


def goatcounter(request):
    return {"goatcounter_url": settings.GOATCOUNTER_URL}


def now_playing(request):
    # only whether a key is set, so the key itself never reaches a template
    return {"now_playing_enabled": bool(settings.LASTFM_API_KEY)}
