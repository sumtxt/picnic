"""
Tests for JSON renderer module
"""

import json
from datetime import date

from src.config import FILTER_PASS, FILTER_OSF_NON_ENGLISH
from src.json_renderer import render_osf_json


def test_render_osf_json_splits_hidden_articles():
    """OSF JSON should separate visible and hidden preprints"""
    articles = [
        {
            "title": "English paper",
            "authors": "Alice",
            "abstract": "English abstract",
            "doi": "https://doi.org/10.31219/osf.io/en123",
            "subjects": [{"id": "polisci", "name": "Political Science"}],
            "id": "en123",
            "version": 1,
            "filter": FILTER_PASS,
            "language": "en",
            "language_score": 0.98,
        },
        {
            "title": "Français",
            "authors": "Bob",
            "abstract": "Résumé",
            "doi": "https://doi.org/10.31219/osf.io/fr123",
            "subjects": [{"id": "polisci", "name": "Political Science"}],
            "id": "fr123",
            "version": 1,
            "filter": FILTER_OSF_NON_ENGLISH,
            "language": "fr",
            "language_score": 0.99,
        },
    ]

    rendered = render_osf_json(articles, date(2026, 7, 29))
    output = json.loads(rendered)

    assert len(output["content"]["articles"]) == 1
    assert len(output["content"]["articles_hidden"]) == 1
    assert output["content"]["articles"][0]["title"] == "English paper"
    assert output["content"]["articles_hidden"][0]["title"] == "Français"
    assert "abstract" in output["content"]["articles"][0]
    assert "abstract" not in output["content"]["articles_hidden"][0]
