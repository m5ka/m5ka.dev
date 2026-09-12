from django.db.models import TextChoices


class ImageSize(TextChoices):
    THUMBNAIL = "thumb", "Thumbnail"
    FULL = "full", "Full"


class MenuHandle(TextChoices):
    HEADER = "header", "Header"
    HAMBURGER = "hamburger", "Hamburger"
    FOOTER = "footer", "Footer"
