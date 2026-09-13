from django.utils.csp import CSP

from .base import *

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

REQUIRE_2FA = True

# Behind Coolify's Traefik proxy, REMOTE_ADDR is the proxy itself. Traefik appends the
# address it saw to X-Forwarded-For, so the right-most entry is the only one a client
# can't spoof. Add another hop here if a CDN (e.g. Cloudflare) is put in front.
AXES_IPWARE_META_PRECEDENCE_ORDER = ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
AXES_IPWARE_PROXY_ORDER = "right-most"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": env("S3_BUCKET_NAME_MEDIA")},
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {"bucket_name": env("S3_BUCKET_NAME_STATIC")},
    },
}

AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL")
AWS_S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY")
AWS_S3_SECRET_ACCESS_KEY = env("S3_SECRET_KEY")
AWS_DEFAULT_ACL = env("S3_DEFAULT_ACL", "public-read")
AWS_S3_SIGNATURE_VERSION = env("S3_SIGNATURE_VERSION", "s3v4")
AWS_QUERYSTRING_AUTH = env.bool("S3_QUERYSTRING_AUTH", False)
AWS_S3_FILE_OVERWRITE = False

# Base URL of a GoatCounter instance, e.g. https://stats.example.com. Its own count.js
# is loaded so that no other third party (like gc.zgo.at) is involved.
# Compose passes an empty string when it's unset, which isn't a valid URL.
if env("GOATCOUNTER_URL", ""):
    GOATCOUNTER_URL = f"https://{env.url('GOATCOUNTER_URL', schemes=['https']).netloc}"

# A new list, as += would also change the one shared with base.py
MIDDLEWARE = [*MIDDLEWARE, "django.middleware.csp.ContentSecurityPolicyMiddleware"]
SECURE_CSP_REPORT_ONLY = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, AWS_S3_ENDPOINT_URL],
    "style-src": [CSP.SELF, AWS_S3_ENDPOINT_URL],
    "font-src": [CSP.SELF, AWS_S3_ENDPOINT_URL],
    "img-src": [CSP.SELF, AWS_S3_ENDPOINT_URL],
    "connect-src": [CSP.SELF],
    "frame-src": ["https://www.youtube-nocookie.com"],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "object-src": [CSP.NONE],
}

if GOATCOUNTER_URL:
    # count.js reports with sendBeacon and falls back to a tracking pixel
    for directive in ("script-src", "connect-src", "img-src"):
        SECURE_CSP_REPORT_ONLY[directive].append(GOATCOUNTER_URL)
