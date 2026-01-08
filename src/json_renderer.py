"""
JSON output rendering for article data

Ported from fun.R:99-120
"""

import json
from typing import List, Dict, Any
from datetime import date

from .config import FILTER_PASS, FILTER_ERROR


def render_json_by_journal(
    articles: List[Dict[str, Any]],
    update_date: date
) -> str:
    """
    Render all articles as a single JSON string grouped by journal ID

    Args:
        articles: List of article dictionaries
        update_date: Date of the crawl

    Returns:
        JSON string containing all journals
    """
    # Group articles by journal ID
    journals_dict = {}

    for article in articles:
        journal_id = article.get("journal_id", "")
        if not journal_id:
            continue  # Skip articles without journal_id

        if journal_id not in journals_dict:
            journals_dict[journal_id] = {
                "journal_id": journal_id,
                "journal_name": article.get("journal_name", ""),
                "articles": [],
                "articles_hidden": []
            }

        # Separate visible articles (filter == 0 or -1) from hidden
        filter_value = article.get("filter", FILTER_PASS)

        if filter_value == FILTER_PASS or filter_value == FILTER_ERROR:
            # Visible articles: include abstract
            article_data = {
                "title": article.get("title"),
                "authors": article.get("authors"),
                "abstract": article.get("abstract"),
                "doi": article.get("doi"),
                "filter": article.get("filter", FILTER_PASS)
            }
            journals_dict[journal_id]["articles"].append(article_data)
        else:
            # Hidden articles: exclude abstract
            article_data = {
                "title": article.get("title"),
                "authors": article.get("authors"),
                "doi": article.get("doi"),
                "filter": article.get("filter", FILTER_PASS)
            }
            journals_dict[journal_id]["articles_hidden"].append(article_data)

    # Sort articles_hidden by filter code for each journal
    for journal_data in journals_dict.values():
        journal_data["articles_hidden"].sort(key=lambda x: x["filter"])

    # Convert to list and sort by journal_id
    content = list(journals_dict.values())
    content.sort(key=lambda x: x["journal_id"])

    # Build final output structure
    output = {
        "update": str(update_date),
        "content": content
    }

    # Render as JSON (pretty-printed)
    return json.dumps(output, indent=2, ensure_ascii=False)


def render_osf_json(articles: List[Dict[str, Any]], update_date: date) -> str:
    """
    Render OSF preprints as JSON with raw level 2 subjects

    Args:
        articles: List of OSF article dictionaries
        update_date: Date of the crawl

    Returns:
        JSON string containing OSF preprints
    """
    article_list = []

    for article in articles:
        # Extract relevant fields for output
        article_data = {
            "title": article.get("title"),
            "authors": article.get("authors"),
            "abstract": article.get("abstract"),
            "doi": article.get("url"),  # Rename url to doi
            "subjects": article.get("subjects", []),  # Keep as array
            "id": article.get("id"),
            "version": article.get("version")
        }
        article_list.append(article_data)

    # Build content structure (no hidden/visible separation)
    content = {
        "articles": article_list
    }

    # Build final output structure
    output = {
        "update": str(update_date),
        "content": content
    }

    # Render as JSON (pretty-printed)
    return json.dumps(output, indent=2, ensure_ascii=False)
