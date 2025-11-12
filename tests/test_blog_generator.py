from types import SimpleNamespace

from src.blog_generator import BlogGenerator


def make_content(idx):
    return SimpleNamespace(
        id=idx,
        category="ai",
        title=f"Sample title {idx}",
        summary="Kısa özet",
        content="Detaylar burada.",
        feed_name="Feed",
        url=f"https://example.com/{idx}",
    )


def test_build_digest_requires_min_items(monkeypatch):
    generator = BlogGenerator()
    monkeypatch.setattr(generator, "select_content_for_blog", lambda: [])
    assert generator.build_digest_package() is None


def test_build_digest_returns_payload(monkeypatch):
    generator = BlogGenerator()
    generator.min_items = 2
    sample_items = [make_content(1), make_content(2)]

    monkeypatch.setattr(generator, "select_content_for_blog", lambda: sample_items)
    monkeypatch.setattr(
        generator,
        "generate_content_section",
        lambda _: "## Highlights\n\nContent",
    )

    digest = generator.build_digest_package()

    assert digest is not None
    assert digest["title"].startswith("Code Report")
    assert "<h3>" in digest["html_content"]  # Markdown converted to Telegraph HTML
    assert digest["content_ids"] == [1, 2]
