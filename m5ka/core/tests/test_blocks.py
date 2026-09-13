import pytest
from django.template import Context, Template
from wagtail.blocks import StreamValue, StructBlockValidationError

from m5ka.core.blocks import (
    CaptionedImageBlock,
    M5kaBlocks,
    QuoteBlock,
    YoutubeEmbedBlock,
)
from m5ka.core.constants import ImageSize
from m5ka.core.tests.utils import create_page


def render_stream(*blocks):
    stream_block = M5kaBlocks()
    value = stream_block.to_python(
        [
            {"type": block_type, "value": value, "id": f"block-{index}"}
            for index, (block_type, value) in enumerate(blocks)
        ]
    )
    assert isinstance(value, StreamValue)
    # mirrors page.html, where headings take their anchor from the loop variable
    template = Template(
        "{% load wagtailcore_tags %}"
        "{% for block in body %}{% include_block block %}{% endfor %}"
    )
    return template.render(Context({"body": value}))


class TestM5kaBlocks:
    def test_available_block_types(self):
        assert list(M5kaBlocks().child_blocks) == [
            "heading",
            "subheading",
            "paragraph",
            "standout_text",
            "image",
            "youtube_embed",
            "divider",
            "page_link",
            "page_cards",
        ]

    def test_renders_heading_with_anchor(self):
        html = render_stream(("heading", "Introduction"))

        assert '<h3 class="heading" id="block-0">Introduction</h3>' in html

    def test_renders_subheading_with_anchor(self):
        html = render_stream(("subheading", "Background"))

        assert '<h4 class="subheading" id="block-0">Background</h4>' in html

    def test_escapes_heading_text(self):
        html = render_stream(("heading", "<script>alert(1)</script>"))

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_renders_paragraph(self):
        html = render_stream(("paragraph", "<p>Some <b>bold</b> prose</p>"))

        assert "Some <b>bold</b> prose" in html

    def test_renders_standout_text(self):
        html = render_stream(("standout_text", "<p>Look at me</p>"))

        assert '<div class="standout">' in html
        assert "Look at me" in html

    def test_renders_divider(self):
        html = render_stream(("divider", None))

        assert '<hr class="divider" />' in html

    def test_renders_youtube_embed(self):
        html = render_stream(("youtube_embed", {"youtube_video_id": "dQw4w9WgXcQ"}))

        assert 'src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"' in html
        assert "www.youtube.com" not in html

    def test_paragraph_features(self):
        assert M5kaBlocks().child_blocks["paragraph"].features == [
            "bold",
            "italic",
            "ol",
            "ul",
            "hr",
            "link",
        ]

    def test_standout_text_features(self):
        assert M5kaBlocks().child_blocks["standout_text"].features == [
            "bold",
            "italic",
            "link",
        ]


class TestQuoteBlock:
    def render(self, **value):
        block = QuoteBlock()
        return block.render(block.to_python({"text": "<p>To be</p>", **value}))

    def test_renders_quote_and_quotee(self):
        html = self.render(quotee="Hamlet")

        assert "<blockquote><p>To be</p></blockquote>" in html
        assert "— Hamlet" in html

    def test_renders_quotee_qualifier(self):
        html = self.render(quotee="Hamlet", quotee_qualifier="Prince of Denmark")

        assert '<span class="qualifier">Prince of Denmark</span>' in html

    def test_omits_empty_quotee_qualifier(self):
        html = self.render(quotee="Hamlet")

        assert "qualifier" not in html

    def test_only_quotee_and_text_are_required(self):
        block = QuoteBlock()

        required = {
            name for name, child in block.child_blocks.items() if child.required
        }
        assert required == {"text", "quotee"}


class TestYoutubeEmbedBlock:
    def test_requires_video_id(self):
        block = YoutubeEmbedBlock()

        with pytest.raises(StructBlockValidationError):
            block.clean(block.to_python({"youtube_video_id": ""}))

    def test_accepts_valid_video_id(self):
        block = YoutubeEmbedBlock()

        value = block.clean(block.to_python({"youtube_video_id": "dQw4w9WgXcQ"}))

        assert value["youtube_video_id"] == "dQw4w9WgXcQ"

    @pytest.mark.parametrize(
        "video_id",
        [
            "dQw4w9WgXc",
            "dQw4w9WgXcQQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            'dQw4w9"><sc',
            "../../evil1",
        ],
    )
    def test_rejects_invalid_video_ids(self, video_id):
        block = YoutubeEmbedBlock()

        with pytest.raises(StructBlockValidationError):
            block.clean(block.to_python({"youtube_video_id": video_id}))


@pytest.mark.django_db
class TestCaptionedImageBlock:
    def render(self, image, **value):
        block = CaptionedImageBlock()
        return block.render(
            block.to_python({"image": {"image": image.pk, "alt_text": "Alt"}, **value})
        )

    def test_defaults_to_full_size(self):
        assert CaptionedImageBlock().child_blocks["size"].get_default() == "full"

    def test_size_choices(self):
        assert ImageSize.values == ["thumb", "full"]

    def test_renders_full_size_image(self, image):
        html = self.render(image, size=ImageSize.FULL)

        rendition = image.get_rendition("width-1200")
        assert '<figure class="image image--full">' in html
        assert f'src="{rendition.url}"' in html

    def test_renders_thumbnail_image(self, image):
        html = self.render(image, size=ImageSize.THUMBNAIL)

        rendition = image.get_rendition("max-380x380")
        assert '<figure class="image image--thumb">' in html
        assert f'src="{rendition.url}"' in html

    def test_renders_caption(self, image):
        html = self.render(image, caption="A lovely picture")

        assert (
            '<figcaption class="image__caption">A lovely picture</figcaption>' in html
        )

    def test_omits_empty_caption(self, image):
        html = self.render(image, caption="")

        assert "figcaption" not in html


@pytest.mark.django_db
class TestPageChooserBlocks:
    def test_renders_page_link(self, home):
        about = create_page(home, "About")

        html = render_stream(("page_link", about.pk))

        assert f'<a class="page-link" href="{about.url}">' in html
        assert '<div class="page-link__title">About</div>' in html

    def test_renders_page_link_search_description_excerpt(self, home):
        about = create_page(home, "About", search_description="A summary of me")

        html = render_stream(("page_link", about.pk))

        assert "A summary of me" in html

    def test_renders_page_link_without_search_description(self, home):
        about = create_page(home, "About", body=[("heading", "All about me")])

        html = render_stream(("page_link", about.pk))

        assert '<div class="page-link__title">About</div>' in html
        assert "page-link__excerpt" not in html
        assert "All about me" not in html

    def test_renders_page_cards(self, home):
        about = create_page(home, "About")
        contact = create_page(home, "Contact")

        html = render_stream(("page_cards", [about.pk, contact.pk]))

        assert '<div class="page-cards">' in html
        assert html.index(about.url) < html.index(contact.url)
