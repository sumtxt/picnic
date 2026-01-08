"""
Tests for OSF parsing functions
"""

import pytest
from src.parsers import (
    get_osf_title,
    get_osf_abstract,
    get_osf_url,
    get_osf_date,
    get_osf_authors,
    get_osf_subjects,
    parse_osf_item,
    parse_osf_response
)


def test_get_osf_title():
    """Test title extraction from OSF item"""
    item = {
        "attributes": {
            "title": "Test Preprint Title"
        }
    }
    assert get_osf_title(item) == "Test Preprint Title"

    # Test missing title
    assert get_osf_title({}) is None
    assert get_osf_title({"attributes": {}}) is None


def test_get_osf_abstract():
    """Test abstract extraction from OSF item"""
    item = {
        "attributes": {
            "description": "This is a test abstract"
        }
    }
    assert get_osf_abstract(item) == "This is a test abstract"

    # Test missing abstract
    assert get_osf_abstract({}) is None
    assert get_osf_abstract({"attributes": {}}) is None


def test_get_osf_url():
    """Test URL extraction from OSF item"""
    item = {
        "links": {
            "preprint_doi": "https://doi.org/10.31219/osf.io/abc123"
        }
    }
    assert get_osf_url(item) == "https://doi.org/10.31219/osf.io/abc123"

    # Test missing URL
    assert get_osf_url({}) is None
    assert get_osf_url({"links": {}}) is None


def test_get_osf_date():
    """Test date extraction from OSF item"""
    item = {
        "attributes": {
            "date_created": "2025-12-20T10:30:00.000000Z"
        }
    }
    assert get_osf_date(item, "date_created") == "2025-12-20"

    # Test different timezone format
    item2 = {
        "attributes": {
            "date_created": "2025-12-20T10:30:00+00:00"
        }
    }
    assert get_osf_date(item2, "date_created") == "2025-12-20"

    # Test missing date
    assert get_osf_date({}, "date_created") is None
    assert get_osf_date({"attributes": {}}, "date_created") is None


def test_get_osf_authors():
    """Test author extraction from OSF item"""
    item = {
        "embeds": {
            "contributors": {
                "data": [
                    {
                        "embeds": {
                            "users": {
                                "data": {
                                    "attributes": {
                                        "full_name": "John Doe"
                                    }
                                }
                            }
                        }
                    },
                    {
                        "embeds": {
                            "users": {
                                "data": {
                                    "attributes": {
                                        "full_name": "Jane Smith"
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
    assert get_osf_authors(item) == "John Doe, Jane Smith"

    # Test empty contributors
    item_empty = {
        "embeds": {
            "contributors": {
                "data": []
            }
        }
    }
    assert get_osf_authors(item_empty) is None


def test_get_osf_subjects():
    """Test subject extraction from OSF item"""
    item = {
        "attributes": {
            "subjects": [
                [
                    {"text": "Social Sciences", "id": "parent1"},
                    {"text": "Political Science", "id": "polisci123"}
                ],
                [
                    {"text": "Social Sciences", "id": "parent1"},
                    {"text": "Economics", "id": "econ456"}
                ]
            ]
        }
    }
    subjects = get_osf_subjects(item)
    assert len(subjects) == 2
    assert subjects[0] == {"id": "polisci123", "name": "Political Science"}
    assert subjects[1] == {"id": "econ456", "name": "Economics"}

    # Check that subject names can be extracted
    subject_names = [s["name"] for s in subjects]
    assert "Political Science" in subject_names
    assert "Economics" in subject_names

    # Test duplicate subjects (same id) are deduplicated
    item_duplicates = {
        "attributes": {
            "subjects": [
                [
                    {"text": "Social Sciences", "id": "parent1"},
                    {"text": "Political Science", "id": "polisci123"}
                ],
                [
                    {"text": "Social Sciences", "id": "parent1"},
                    {"text": "Political Science", "id": "polisci123"}
                ]
            ]
        }
    }
    subjects_dedup = get_osf_subjects(item_duplicates)
    assert len(subjects_dedup) == 1
    assert subjects_dedup[0] == {"id": "polisci123", "name": "Political Science"}

    # Test empty subjects
    item_empty = {
        "attributes": {
            "subjects": []
        }
    }
    assert get_osf_subjects(item_empty) == []


def test_parse_osf_item():
    """Test complete OSF item parsing"""
    item = {
        "attributes": {
            "title": "Test Title",
            "description": "Test abstract",
            "date_created": "2025-12-20T10:30:00Z",
            "subjects": [
                [
                    {"text": "Social Sciences", "id": "parent1"},
                    {"text": "Political Science", "id": "polisci123"}
                ]
            ]
        },
        "links": {
            "preprint_doi": "https://doi.org/10.31219/osf.io/abc123"
        },
        "embeds": {
            "contributors": {
                "data": [
                    {
                        "embeds": {
                            "users": {
                                "data": {
                                    "attributes": {
                                        "full_name": "John Doe"
                                    }
                                }
                            }
                        }
                    }
                ]
            }
        }
    }

    article = parse_osf_item(item)
    assert article["title"] == "Test Title"
    assert article["abstract"] == "Test abstract"
    assert article["url"] == "https://doi.org/10.31219/osf.io/abc123"
    assert article["created"] == "2025-12-20"
    assert article["authors"] == "John Doe"
    # Check subjects is a list of dictionaries
    assert isinstance(article["subjects"], list)
    assert len(article["subjects"]) == 1
    assert article["subjects"][0] == {"id": "polisci123", "name": "Political Science"}


def test_parse_osf_response():
    """Test parsing multiple OSF items"""
    items = [
        {
            "attributes": {
                "title": "Article 1",
                "description": "Abstract 1",
                "date_created": "2025-12-20T10:30:00Z",
                "subjects": [
                    [
                        {"text": "Social Sciences", "id": "parent1"},
                        {"text": "Economics", "id": "econ456"}
                    ]
                ]
            },
            "links": {
                "preprint_doi": "https://doi.org/10.31219/osf.io/abc123"
            },
            "embeds": {
                "contributors": {
                    "data": []
                }
            }
        }
    ]

    articles = parse_osf_response(items)
    assert len(articles) == 1
    assert articles[0]["title"] == "Article 1"
    # Check subjects is a list of dictionaries
    assert isinstance(articles[0]["subjects"], list)
    assert len(articles[0]["subjects"]) == 1
    assert articles[0]["subjects"][0] == {"id": "econ456", "name": "Economics"}
