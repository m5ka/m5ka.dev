import pytest
from pytest_django.asserts import assertTemplateUsed
from wagtail.models import Page

from m5ka.core.models import BlogPost, BlogRoot
from m5ka.core.models import Page as ContentPage
from m5ka.core.tests.utils import create_page, create_post, make_private
from m5ka.home.models import HomePage


def titles(pages):
    return [page.title for page in pages]


@pytest.mark.django_db
class TestPageTypeRules:
    def test_blog_root_can_only_be_created_under_home(self, home, root):
        about = create_page(home, "About")

        assert BlogRoot.can_create_at(home)
        assert not BlogRoot.can_create_at(root)
        assert not BlogRoot.can_create_at(about)

    def test_only_one_blog_root_is_allowed(self, home, blog_root):
        assert not BlogRoot.can_create_at(home)

    def test_blog_posts_can_only_be_created_under_blog_root(self, home, blog_root):
        about = create_page(home, "About")

        assert BlogPost.can_create_at(blog_root)
        assert not BlogPost.can_create_at(home)
        assert not BlogPost.can_create_at(about)

    def test_blog_posts_have_no_children(self, blog_root):
        post = create_post(blog_root, "Hello")

        assert not ContentPage.can_create_at(post)
        assert not BlogPost.can_create_at(post)

    def test_blog_root_only_allows_blog_posts(self, blog_root):
        assert blog_root.specific_class.allowed_subpage_models() == [BlogPost]

    def test_pages_can_be_nested_under_home_and_pages(self, home, root):
        about = create_page(home, "About")

        assert ContentPage.can_create_at(home)
        assert ContentPage.can_create_at(about)
        assert not ContentPage.can_create_at(root)

    def test_home_page_subpage_types(self):
        assert set(HomePage.allowed_subpage_models()) == {BlogRoot, ContentPage}


@pytest.mark.django_db
class TestBlogRootPosts:
    def test_lists_live_child_posts(self, blog_root):
        create_post(blog_root, "First")
        create_post(blog_root, "Second")

        assert titles(blog_root.posts) == ["First", "Second"]

    def test_excludes_draft_posts(self, blog_root):
        create_post(blog_root, "Published")
        create_post(blog_root, "Draft", live=False)

        assert titles(blog_root.posts) == ["Published"]

    def test_excludes_private_posts(self, blog_root):
        create_post(blog_root, "Published")
        make_private(create_post(blog_root, "Private"))

        assert titles(blog_root.posts) == ["Published"]

    def test_empty_when_no_posts(self, blog_root):
        assert not blog_root.posts.exists()

    def test_returns_specific_blog_posts(self, blog_root):
        create_post(blog_root, "First")

        assert isinstance(blog_root.posts.first(), BlogPost)


@pytest.mark.django_db
class TestHomePagePosts:
    def test_lists_live_posts_from_blog(self, home, blog_root):
        create_post(blog_root, "Published")
        create_post(blog_root, "Draft", live=False)

        assert titles(home.posts) == ["Published"]

    def test_excludes_private_posts(self, home, blog_root):
        create_post(blog_root, "Published")
        make_private(create_post(blog_root, "Private"))

        assert titles(home.posts) == ["Published"]

    def test_excludes_posts_of_private_blog(self, home, blog_root):
        create_post(blog_root, "Published")
        make_private(blog_root)

        assert titles(home.posts) == []

    def test_excludes_non_post_pages(self, home, blog_root):
        create_page(home, "About")
        create_post(blog_root, "Published")

        assert titles(home.posts) == ["Published"]

    def test_excludes_posts_outside_of_home(self, home, root, blog_root):
        other_home = root.add_child(instance=HomePage(title="Other", slug="other"))
        other_blog = other_home.add_child(instance=BlogRoot(title="B", slug="b"))
        create_post(blog_root, "Mine")
        create_post(other_blog, "Theirs")

        assert titles(home.posts) == ["Mine"]


@pytest.mark.django_db
class TestBlogRootView:
    def test_renders_live_posts(self, client, blog_root):
        published = create_post(blog_root, "Published")
        create_post(blog_root, "Draft", live=False)

        response = client.get(blog_root.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert f'href="{published.url}"' in content
        assert "Published" in content
        assert "Draft" not in content

    def test_renders_with_no_posts(self, client, blog_root):
        response = client.get(blog_root.url)

        assert response.status_code == 200
        assertTemplateUsed(response, "m5ka_core/blog_root.html")

    def test_renders_search_description_excerpt(self, client, blog_root):
        create_post(blog_root, "Post", search_description="A handwritten summary")

        response = client.get(blog_root.url)

        assert "A handwritten summary" in response.content.decode()

    def test_does_not_use_body_as_excerpt(self, client, blog_root):
        create_post(blog_root, "Post", body=[("heading", "An excerpt from the body")])

        response = client.get(blog_root.url)

        content = response.content.decode()
        assert "page-link__excerpt" not in content
        assert "An excerpt from the body" not in content

    def test_renders_long_excerpts_in_full(self, client, blog_root):
        create_post(blog_root, "Post", search_description="x" * 500)

        response = client.get(blog_root.url)

        assert (
            f'<div class="page-link__excerpt">{"x" * 500}</div>'
            in response.content.decode()
        )

    def test_renders_headline_image_thumbnail(self, client, blog_root, image):
        create_post(blog_root, "Post", headline_image=image)

        response = client.get(blog_root.url)

        rendition = image.get_rendition("fill-400x300|format-webp")
        assert f'src="{rendition.url}"' in response.content.decode()


@pytest.mark.django_db
class TestBlogPostView:
    def test_renders_title_and_body(self, client, blog_root):
        post = create_post(
            blog_root, "Hello world", body=[("paragraph", "<p>Some prose</p>")]
        )

        response = client.get(post.url)

        assert response.status_code == 200
        assertTemplateUsed(response, "m5ka_core/blog_post.html")
        content = response.content.decode()
        assert '<h2 class="main__title">Hello world</h2>' in content
        assert "Some prose" in content

    def test_renders_headline_image(self, client, blog_root, image):
        post = create_post(blog_root, "Post", headline_image=image)

        response = client.get(post.url)

        rendition = image.get_rendition("fill-1920x480|format-webp")
        assert f'src="{rendition.url}"' in response.content.decode()
        assert 'class="headline-image"' in response.content.decode()

    def test_omits_headline_image_when_unset(self, client, blog_root):
        post = create_post(blog_root, "Post")

        response = client.get(post.url)

        assert 'class="headline-image"' not in response.content.decode()

    def test_headline_image_is_cleared_when_image_is_deleted(self, blog_root, image):
        post = create_post(blog_root, "Post", headline_image=image)

        image.delete()

        post.refresh_from_db()
        assert post.headline_image is None

    def test_draft_post_is_not_found(self, client, blog_root):
        post = create_post(blog_root, "Draft", live=False)

        response = client.get(Page.objects.get(pk=post.pk).get_url())

        assert response.status_code == 404


@pytest.mark.django_db
class TestHomePageView:
    def test_renders_post_list(self, client, home, blog_root):
        post = create_post(blog_root, "Published")
        create_post(blog_root, "Draft", live=False)

        response = client.get(home.url)

        assert response.status_code == 200
        content = response.content.decode()
        assert 'class="blog-title"' in content
        assert f'href="{post.url}"' in content
        assert "Draft" not in content

    def test_does_not_link_private_posts(self, client, home, blog_root):
        create_post(blog_root, "Published")
        private = make_private(create_post(blog_root, "Private"))

        response = client.get(home.url)

        content = response.content.decode()
        assert "Private" not in content
        assert f'href="{private.url}"' not in content

    def test_private_post_asks_for_password(self, client, blog_root):
        post = make_private(create_post(blog_root, "Private", search_description="x"))

        response = client.get(post.url)

        assert response.status_code == 200
        assertTemplateUsed(response, "wagtailcore/password_required.html")

    def test_omits_post_list_without_posts(self, client, home, blog_root):
        create_post(blog_root, "Draft", live=False)

        response = client.get(home.url)

        assert response.status_code == 200
        assert 'class="blog-title"' not in response.content.decode()
