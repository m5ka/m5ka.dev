from .base import *  # noqa: F403

DEBUG = False

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
AWS_S3_SIGNATURE_VERSION = env("S3_SIGNATURE_VERSION", "s3")
AWS_QUERYSTRING_AUTH = env.bool("S3_QUERYSTRING_AUTH", False)
