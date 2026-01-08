"""
Tests for parsers module
"""

import pytest
from src.parsers import (
    extract_title,
    extract_authors,
    extract_author_name,
    extract_date,
    extract_abstract,
    extract_url,
    parse_crossref_item
)


class TestExtractTitle:
    def test_extract_title_from_list(self):
        item = {"title": ["Sample Article Title"]}
        assert extract_title(item) == "Sample Article Title"

    def test_extract_title_missing(self):
        item = {}
        assert extract_title(item) is None

    def test_extract_title_none(self):
        item = {"title": None}
        assert extract_title(item) is None


class TestExtractAuthors:
    def test_extract_single_author(self):
        item = {
            "author": [
                {"given": "John", "family": "Doe"}
            ]
        }
        assert extract_authors(item) == "John Doe"

    def test_extract_multiple_authors(self):
        item = {
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"}
            ]
        }
        assert extract_authors(item) == "John Doe, Jane Smith"

    def test_extract_authors_missing(self):
        item = {}
        assert extract_authors(item) is None

    def test_extract_authors_empty_list(self):
        item = {"author": []}
        assert extract_authors(item) is None


class TestExtractDate:
    def test_extract_date_full(self):
        item = {
            "created": {
                "date-parts": [[2024, 12, 15]]
            }
        }
        assert extract_date(item, "created") == "2024-12-15"

    def test_extract_date_year_month(self):
        item = {
            "created": {
                "date-parts": [[2024, 12]]
            }
        }
        assert extract_date(item, "created") == "2024-12"

    def test_extract_date_missing(self):
        item = {}
        assert extract_date(item, "created") is None


class TestExtractAbstract:
    def test_extract_abstract(self):
        item = {"abstract": "This is a test abstract."}
        assert extract_abstract(item) == "This is a test abstract."

    def test_extract_abstract_missing(self):
        item = {}
        assert extract_abstract(item) is None


class TestExtractUrl:
    def test_extract_url(self):
        item = {"URL": "https://doi.org/10.1234/example"}
        assert extract_url(item) == "https://doi.org/10.1234/example"

    def test_extract_url_missing(self):
        item = {}
        assert extract_url(item) is None


class TestParseCrossrefItem:
    def test_parse_complete_item(self):
        item = {
            "title": ["Test Article"],
            "author": [{"given": "John", "family": "Doe"}],
            "created": {"date-parts": [[2024, 12, 15]]},
            "abstract": "Test abstract",
            "URL": "https://doi.org/10.1234/test",
            "_issn": "1234-5678"
        }

        result = parse_crossref_item(item)

        assert result["title"] == "Test Article"
        assert result["authors"] == "John Doe"
        assert result["created"] == "2024-12-15"
        assert result["abstract"] == "Test abstract"
        assert result["url"] == "https://doi.org/10.1234/test"
        assert result["issn"] == "1234-5678"

    def test_parse_minimal_item(self):
        item = {"_issn": "1234-5678"}

        result = parse_crossref_item(item)

        assert result["title"] is None
        assert result["authors"] is None
        assert result["abstract"] is None
        assert result["url"] is None
        assert result["issn"] == "1234-5678"
