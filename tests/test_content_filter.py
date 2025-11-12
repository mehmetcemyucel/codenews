from types import SimpleNamespace

import pytest

from src.config import Config
from src.content_filter import ContentFilter


@pytest.fixture(autouse=True)
def reset_keywords():
    original = Config.KEYWORDS
    yield
    Config.KEYWORDS = original


def test_categorize_content_detects_keyword(monkeypatch):
    """Categorization should flag content when unified keywords match."""
    monkeypatch.setattr(Config, "KEYWORDS", ["artificial intelligence"])
    content_filter = ContentFilter()

    sample = SimpleNamespace(
        title="Artificial Intelligence hits new milestone",
        summary="",
        content="",
        category="ai",
    )

    category, score = content_filter.categorize_content(sample)
    assert category == "ai"
    assert score > 0


def test_categorize_content_returns_none_without_match(monkeypatch):
    """Irrelevant content should not pass the filter."""
    monkeypatch.setattr(Config, "KEYWORDS", ["artificial intelligence"])
    content_filter = ContentFilter()

    sample = SimpleNamespace(
        title="Garden tips for spring planting",
        summary="",
        content="",
        category="lifestyle",
    )

    category, score = content_filter.categorize_content(sample)
    assert category is None
    assert score == 0
