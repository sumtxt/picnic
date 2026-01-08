"""
Filtering logic for articles

Ported from fun.R:42-93
"""

import re
import logging
from typing import Dict, Any, List, Optional

from .config import (
    FILTER_PASS,
    FILTER_STANDARD,
    FILTER_SCIENCE,
    FILTER_NATURE,
    ENABLE_AI_FILTER
)
from .openai_client import classify_article, create_openai_client


def apply_standard_filter(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply standard filter to detect ToCs, editorials, and errata

    Ported from fun.R:83-93

    Args:
        article: Article dictionary

    Returns:
        Article with 'filter' field added
    """
    title = article.get("title")

    flag = FILTER_PASS

    # Check for missing title (ToCs often have no title)
    if title is None or title == "":
        flag = FILTER_STANDARD

    # Check for specific editorial titles
    elif title == "Editorial Board":
        flag = FILTER_STANDARD
    elif title == "Issue Information":
        flag = FILTER_STANDARD
    elif title == "Forthcoming Papers":
        flag = FILTER_STANDARD

    # Check for errata and other metadata
    elif re.search(
        r'ERRATUM|ERRATA|Frontmatter|Front matter|Backmatter|Back matter',
        title,
        re.IGNORECASE
    ):
        flag = FILTER_STANDARD

    article["filter"] = flag
    return article


def apply_science_filter(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply Science journal filter (abstract length check)

    Ported from fun.R:71-76

    Args:
        article: Article dictionary

    Returns:
        Article with 'filter' field updated
    """
    abstract = article.get("abstract")

    # Flag if abstract is missing or too short (< 200 chars)
    if abstract is None or len(abstract) < 200:
        article["filter"] = FILTER_SCIENCE
    else:
        article["filter"] = FILTER_PASS

    return article


def apply_nature_filter(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply Nature journal filter (URL pattern check)

    Ported from fun.R:78-81

    Args:
        article: Article dictionary

    Returns:
        Article with 'filter' field updated
    """
    url = article.get("url", "")

    # Nature research articles have "/s" in the URL
    # Articles without "/s" are filtered out
    if "/s" not in url:
        article["filter"] = FILTER_NATURE
    else:
        article["filter"] = FILTER_PASS

    return article


def apply_filter_by_name(
    article: Dict[str, Any],
    filter_name: str,
    openai_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Apply a single filter to an article by filter name

    Args:
        article: Article dictionary
        filter_name: Name of filter to apply ('science', 'nature', or 'ai')
        openai_client: OpenAI client for AI filtering

    Returns:
        Article with filter applied
    """
    if filter_name == "science":
        return apply_science_filter(article)
    elif filter_name == "nature":
        return apply_nature_filter(article)
    elif filter_name == "ai":
        return apply_multidisciplinary_filter(article, openai_client)
    else:
        logging.warning(f"Unknown filter name: {filter_name}")
        return article


def apply_multidisciplinary_filter(
    article: Dict[str, Any],
    openai_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Apply AI-powered multidisciplinary filter

    Ported from fun.R:42-60 and crawl.R:54-61

    Args:
        article: Article dictionary
        openai_client: OpenAI client (creates new one if None)

    Returns:
        Article with 'filter' field updated
    """
    # If already filtered by standard filter, keep that
    current_filter = article.get("filter", FILTER_PASS)
    if current_filter != FILTER_PASS:
        return article

    # Log progress
    url = article.get("url", "unknown")
    logging.info(f"AI classifying: {url}")

    # Classify using OpenAI
    journal = article.get("journal_name", "")
    title = article.get("title", "")
    abstract = article.get("abstract", "")

    try:
        filter_result = classify_article(
            journal=journal,
            title=title,
            abstract=abstract,
            client=openai_client
        )
        article["filter"] = filter_result
    except Exception as e:
        logging.error(f"Error in multidisciplinary filter for {url}: {e}")
        article["filter"] = FILTER_PASS  # Use -1 in actual implementation

    return article


def apply_all_filters(
    articles: List[Dict[str, Any]],
    openai_client: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Apply all appropriate filters to articles

    Filters are applied in this order:
    1. Standard filter (ToC, editorial, erratum detection) - applied to ALL articles
    2. Journal-specific filters from 'filters' array - applied in order: nature, science, then ai

    Args:
        articles: List of article dictionaries
        openai_client: OpenAI client for AI filtering

    Returns:
        Filtered articles
    """
    # Step 1: Apply standard filter to all articles
    articles = [apply_standard_filter(article) for article in articles]

    # Step 2: Apply journal-specific filters in order
    # Check if any articles need AI filtering
    needs_ai = any("ai" in article.get("filters", []) for article in articles)
    if needs_ai and ENABLE_AI_FILTER and openai_client is None:
        openai_client = create_openai_client()

    # Apply filters to each article
    for article in articles:
        filters_to_apply = article.get("filters", [])

        if not filters_to_apply:
            continue

        # Apply filters in the correct order: nature, science, then ai
        # This ensures nature/science filters run before AI filter
        filter_order = ["nature", "science", "ai"]

        for filter_name in filter_order:
            if filter_name in filters_to_apply:
                # Skip AI filter if disabled in config
                if filter_name == "ai" and not ENABLE_AI_FILTER:
                    logging.info("AI filter disabled in config (ENABLE_AI_FILTER=False)")
                    continue
                # Apply the filter
                # Note: The AI filter has built-in logic to skip if already filtered
                article = apply_filter_by_name(article, filter_name, openai_client)

    return articles
