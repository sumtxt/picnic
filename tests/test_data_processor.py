"""
Tests for data_processor module
"""

import pytest
from src.data_processor import (
    strip_html,
    extract_doi,
    deduplicate_articles,
    remove_past_articles,
    load_past_dois,
    update_doi_memory
)


class TestStripHtml:
    def test_strip_simple_html(self):
        text = "<p>This is a test</p>"
        assert strip_html(text) == "This is a test"

    def test_strip_multiple_tags(self):
        text = "<p>This is <strong>bold</strong> text</p>"
        assert strip_html(text) == "This is bold text"

    def test_strip_with_whitespace(self):
        text = "<p>This   has    multiple   spaces</p>"
        assert strip_html(text) == "This has multiple spaces"

    def test_strip_none(self):
        assert strip_html(None) is None

    def test_strip_empty_string(self):
        result = strip_html("")
        assert result is None or result == ""


class TestExtractDoi:
    def test_extract_doi_with_https(self):
        url = "https://dx.doi.org/10.1234/example"
        assert extract_doi(url) == "10.1234/example"

    def test_extract_doi_with_http(self):
        url = "http://dx.doi.org/10.1234/example"
        assert extract_doi(url) == "10.1234/example"

    def test_extract_doi_with_doi_org(self):
        url = "https://doi.org/10.1234/example"
        assert extract_doi(url) == "10.1234/example"

    def test_extract_doi_http_doi_org(self):
        url = "http://doi.org/10.1234/example"
        assert extract_doi(url) == "10.1234/example"

    def test_extract_doi_already_clean(self):
        url = "10.1234/example"
        assert extract_doi(url) == "10.1234/example"

    def test_extract_doi_none(self):
        assert extract_doi(None) is None


class TestDeduplicateArticles:
    def test_deduplicate_by_url(self):
        articles = [
            {"url": "https://doi.org/10.1234/a", "title": "Article A"},
            {"url": "https://doi.org/10.1234/b", "title": "Article B"},
            {"url": "https://doi.org/10.1234/a", "title": "Article A Duplicate"},
        ]

        result = deduplicate_articles(articles)

        assert len(result) == 2
        assert result[0]["url"] == "https://doi.org/10.1234/a"
        assert result[1]["url"] == "https://doi.org/10.1234/b"

    def test_deduplicate_empty_list(self):
        assert deduplicate_articles([]) == []

    def test_deduplicate_no_duplicates(self):
        articles = [
            {"url": "https://doi.org/10.1234/a"},
            {"url": "https://doi.org/10.1234/b"},
        ]

        result = deduplicate_articles(articles)
        assert len(result) == 2


class TestRemovePastArticles:
    def test_remove_past_articles(self):
        articles = [
            {"url": "http://dx.doi.org/10.1234/new1"},
            {"url": "http://dx.doi.org/10.1234/old1"},
            {"url": "http://dx.doi.org/10.1234/new2"},
        ]

        # past_urls now contains DOIs without prefix
        past_urls = {"10.1234/old1"}

        result = remove_past_articles(articles, past_urls)

        assert len(result) == 2
        assert all(a["url"] != "http://dx.doi.org/10.1234/old1" for a in result)

    def test_remove_all_past(self):
        articles = [
            {"url": "http://dx.doi.org/10.1234/old1"},
            {"url": "http://dx.doi.org/10.1234/old2"},
        ]

        # past_urls now contains DOIs without prefix
        past_urls = {
            "10.1234/old1",
            "10.1234/old2"
        }

        result = remove_past_articles(articles, past_urls)
        assert len(result) == 0

    def test_remove_none_past(self):
        articles = [
            {"url": "http://dx.doi.org/10.1234/new1"},
            {"url": "http://dx.doi.org/10.1234/new2"},
        ]

        past_urls = set()

        result = remove_past_articles(articles, past_urls)
        assert len(result) == 2

    def test_remove_past_articles_with_full_url_in_past(self):
        # Test backward compatibility: past_dois might still contain full URLs from old data
        # load_past_dois now extracts DOIs, so this simulates that scenario
        articles = [
            {"url": "http://dx.doi.org/10.1234/new1"},
            {"url": "http://dx.doi.org/10.1234/old1"},
        ]

        # Simulate past_dois after being processed by load_past_dois (which extracts DOIs)
        past_dois = {"10.1234/old1"}

        result = remove_past_articles(articles, past_dois)

        assert len(result) == 1
        assert result[0]["url"] == "http://dx.doi.org/10.1234/new1"
