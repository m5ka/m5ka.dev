from django.core.validators import RegexValidator
from wagtail.blocks import (
    CharBlock,
    ChoiceBlock,
    ListBlock,
    PageChooserBlock,
    RichTextBlock,
    StaticBlock,
    StreamBlock,
    StructBlock,
)
from wagtail.images.blocks import ImageBlock

from m5ka.core.constants import ImageSize


class CaptionedImageBlock(StructBlock):
    image = ImageBlock()
    caption = CharBlock(required=False)
    size = ChoiceBlock(choices=ImageSize.choices, default=ImageSize.FULL)

    class Meta:
        icon = "image"
        template = "blocks/image.html"


class QuoteBlock(StructBlock):
    text = RichTextBlock(features=["bold", "italic"])
    quotee = CharBlock(help_text="Who originally said or wrote this quote")
    quotee_qualifier = CharBlock(
        required=False,
        help_text=(
            "An optional qualifier for the quotee, such as their profession or role"
        ),
    )
    date = CharBlock(
        required=False,
        help_text="An optional date for when this quote was said or written",
    )
    context = CharBlock(
        required=False,
        help_text="An optional context for the quote, such as the work it comes from",
    )

    class Meta:
        icon = "openquote"
        template = "blocks/quote.html"


class YoutubeEmbedBlock(StructBlock):
    youtube_video_id = CharBlock(
        label="YouTube video ID",
        help_text="This is just the part after ?v= in the URL",
        validators=[
            RegexValidator(r"^[A-Za-z0-9_-]{11}$", "Enter the 11-character video ID")
        ],
    )

    class Meta:
        icon = "media"
        template = "blocks/youtube_embed.html"
        label = "YouTube embed"


class M5kaBlocks(StreamBlock):
    heading = CharBlock(icon="title", template="blocks/heading.html")
    subheading = CharBlock(icon="h2", template="blocks/subheading.html")
    paragraph = RichTextBlock(features=["bold", "italic", "ol", "ul", "hr", "link"])
    standout_text = RichTextBlock(
        features=["bold", "italic", "link"], template="blocks/standout_text.html"
    )
    image = CaptionedImageBlock()
    youtube_embed = YoutubeEmbedBlock()
    divider = StaticBlock(icon="minus", template="blocks/divider.html")
    page_link = PageChooserBlock(icon="link", template="blocks/page_link.html")
    page_cards = ListBlock(
        PageChooserBlock(), icon="table", template="blocks/page_cards.html"
    )
