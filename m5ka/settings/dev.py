from .base import *

DEBUG = True

MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"
