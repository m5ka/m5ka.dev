from django.db.models import TextChoices


class ImageSize(TextChoices):
    THUMBNAIL = "thumb", "Thumbnail"
    FULL = "full", "Full"
