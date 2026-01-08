"""
Tests for filters module
"""

import pytest
from src.filters import (
    apply_standard_filter,
    apply_science_filter,
    apply_nature_filter
)
from src.config import FILTER_PASS, FILTER_STANDARD, FILTER_SCIENCE, FILTER_NATURE


class TestStandardFilter:
    def test_pass_normal_article(self):
        article = {"title": "Democracy in the 21st Century"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_PASS

    def test_filter_editorial_board(self):
        article = {"title": "Editorial Board"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_issue_information(self):
        article = {"title": "Issue Information"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_forthcoming_papers(self):
        article = {"title": "Forthcoming Papers"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_erratum(self):
        article = {"title": "ERRATUM: Original article"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_errata(self):
        article = {"title": "Errata for Volume 12"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_frontmatter(self):
        article = {"title": "Frontmatter"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_backmatter(self):
        article = {"title": "Back matter"}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_missing_title(self):
        article = {"title": None}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD

    def test_filter_empty_title(self):
        article = {"title": ""}
        result = apply_standard_filter(article)
        assert result["filter"] == FILTER_STANDARD


class TestScienceFilter:
    def test_pass_long_abstract(self):
        article = {"abstract": "A" * 250}
        result = apply_science_filter(article)
        assert result["filter"] == FILTER_PASS

    def test_filter_short_abstract(self):
        article = {"abstract": "Short abstract"}
        result = apply_science_filter(article)
        assert result["filter"] == FILTER_SCIENCE

    def test_filter_missing_abstract(self):
        article = {"abstract": None}
        result = apply_science_filter(article)
        assert result["filter"] == FILTER_SCIENCE

    def test_filter_exactly_200_chars(self):
        article = {"abstract": "A" * 200}
        result = apply_science_filter(article)
        assert result["filter"] == FILTER_PASS


class TestNatureFilter:
    def test_pass_research_article(self):
        article = {"url": "https://www.nature.com/articles/s41586-024-12345-6"}
        result = apply_nature_filter(article)
        assert result["filter"] == FILTER_PASS

    def test_filter_non_research(self):
        article = {"url": "https://www.nature.com/articles/d41586-024-12345-6"}
        result = apply_nature_filter(article)
        assert result["filter"] == FILTER_NATURE

    def test_filter_missing_url(self):
        article = {}
        result = apply_nature_filter(article)
        assert result["filter"] == FILTER_NATURE
