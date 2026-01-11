"""
Tests for OSF data processing functions
"""

import pytest
from src.data_processor import (
    strip_whitespace,
    extract_doi,
    extract_osf_id_and_version,
    deduplicate_osf_versions,
    remove_past_osf_preprints,
    clean_osf_data
)


def test_strip_whitespace():
    """Test whitespace stripping"""
    assert strip_whitespace("  test  ") == "test"
    assert strip_whitespace("test   multiple   spaces") == "test multiple spaces"
    assert strip_whitespace("\n\t test \n") == "test"
    assert strip_whitespace(None) is None
    assert strip_whitespace("   ") is None


def test_extract_doi_osf():
    """Test DOI extraction from OSF URLs"""
    assert extract_doi("https://doi.org/10.31219/osf.io/abc123") == "10.31219/osf.io/abc123"
    assert extract_doi("http://doi.org/10.31219/osf.io/xyz789") == "10.31219/osf.io/xyz789"
    assert extract_doi("https://dx.doi.org/10.31219/osf.io/abc123") == "10.31219/osf.io/abc123"
    assert extract_doi("http://dx.doi.org/10.31219/osf.io/xyz789") == "10.31219/osf.io/xyz789"
    assert extract_doi("10.31219/osf.io/test") == "10.31219/osf.io/test"
    assert extract_doi(None) is None


def test_extract_osf_id_and_version():
    """Test OSF ID and version extraction"""
    # With version
    osf_id, version = extract_osf_id_and_version("https://doi.org/10.31219/osf.io/abc123_v2")
    assert osf_id == "abc123"
    assert version == 2

    # Without version
    osf_id, version = extract_osf_id_and_version("https://doi.org/10.31219/osf.io/xyz789")
    assert osf_id == "xyz789"
    assert version == 1

    # Multiple digit version
    osf_id, version = extract_osf_id_and_version("https://doi.org/10.31219/osf.io/test_v15")
    assert osf_id == "test"
    assert version == 15

    # None input
    osf_id, version = extract_osf_id_and_version(None)
    assert osf_id is None
    assert version is None


def test_deduplicate_osf_versions():
    """Test OSF version deduplication"""
    articles = [
        {"url": "https://doi.org/10.31219/osf.io/abc123_v1", "title": "Article 1 v1"},
        {"url": "https://doi.org/10.31219/osf.io/abc123_v2", "title": "Article 1 v2"},
        {"url": "https://doi.org/10.31219/osf.io/xyz789_v1", "title": "Article 2 v1"}
    ]

    result = deduplicate_osf_versions(articles)

    # Should keep only latest version of abc123 and xyz789
    assert len(result) == 2

    # Find the abc123 article
    abc_article = next(a for a in result if a["id"] == "abc123")
    assert abc_article["version"] == 2
    assert abc_article["title"] == "Article 1 v2"

    # Find the xyz789 article
    xyz_article = next(a for a in result if a["id"] == "xyz789")
    assert xyz_article["version"] == 1


def test_remove_past_osf_preprints():
    """Test filtering of past OSF preprints"""
    articles = [
        {"id": "abc123", "title": "New Article"},
        {"id": "xyz789", "title": "Old Article"},
        {"id": "def456", "title": "Another New Article"}
    ]

    past_ids = {"xyz789"}

    result = remove_past_osf_preprints(articles, past_ids)

    assert len(result) == 2
    assert all(a["id"] != "xyz789" for a in result)
    assert any(a["id"] == "abc123" for a in result)
    assert any(a["id"] == "def456" for a in result)


def test_clean_osf_data():
    """Test OSF data cleaning"""
    articles = [
        {
            "title": "  Test   Title  ",
            "abstract": "Test  \n  abstract   ",
            "url": "https://doi.org/10.31219/osf.io/abc123"
        }
    ]

    result = clean_osf_data(articles)

    assert result[0]["title"] == "Test Title"
    assert result[0]["abstract"] == "Test abstract"
    assert result[0]["doi"] == "10.31219/osf.io/abc123"
