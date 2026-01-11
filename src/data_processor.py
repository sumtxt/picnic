"""
Data processing utilities for cleaning and deduplication

Ported from fun.R:122-143 and crawl.R:38-44
"""

import re
import os
import logging
import json
from typing import List, Dict, Any, Set, Optional, Tuple
from collections import defaultdict

from .config import PARAMETERS_DIR, MEMORY_DIR


def strip_html(text: Optional[str]) -> Optional[str]:
    """
    Remove HTML tags from text

    Ported from fun.R:126-134

    Args:
        text: Text potentially containing HTML

    Returns:
        Clean text with HTML removed, or None
    """
    if text is None:
        return None

    # Remove HTML tags
    text = re.sub(r'<.*?>', ' ', text)

    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text)

    # Trim whitespace
    text = text.strip()

    return text if text else None


def extract_doi(url: Optional[str]) -> Optional[str]:
    """
    Extract DOI from URL

    Supports both https://dx.doi.org/ and https://doi.org/ prefixes

    Ported from fun.R:122-124

    Args:
        url: Article URL (typically DOI URL)

    Returns:
        DOI string or original URL
    """
    if url is None:
        return None

    # Remove http(s)://dx.doi.org/ or http(s)://doi.org/ prefix
    doi = re.sub(r'https?://(dx\.)?doi\.org/', '', url)

    return doi


def load_journals() -> List[Dict[str, Any]]:
    """
    Load journal configuration from journals.json

    Returns:
        List of journal dictionaries
    """
    filepath = os.path.join(PARAMETERS_DIR, "journals.json")

    if not os.path.exists(filepath):
        logging.error(f"Journal file not found: {filepath}")
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            journals = json.load(f)
            # Normalize fields if necessary (already pretty clean in JSON)
            return journals
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error reading journal file {filepath}: {e}")
        return []


def load_past_dois() -> Set[str]:
    """
    Load all previously crawled DOIs from plain text file

    Returns:
        Set of DOIs (without http://dx.doi.org/ prefix)
    """
    filepath = os.path.join(MEMORY_DIR, "doi.txt")

    if not os.path.exists(filepath):
        logging.warning(f"DOI memory file not found: {filepath}. Creating new one.")
        # Create empty file
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                pass  # Create empty file
        except IOError as e:
            logging.error(f"Error creating DOI memory file: {e}")
        return set()

    dois = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                doi_value = line.strip()
                if doi_value:
                    # Extract DOI to normalize (handles both old full URLs and new DOI-only format)
                    doi = extract_doi(doi_value)
                    if doi:
                        dois.add(doi)
    except IOError as e:
        logging.error(f"Error reading DOI memory file {filepath}: {e}")

    return dois


def update_doi_memory(urls: List[str]) -> None:
    """
    Append new DOIs to memory file (plain text format)

    Stores DOIs without the http://dx.doi.org/ prefix

    Args:
        urls: List of URLs to extract DOIs from and append
    """
    if not urls:
        return

    filepath = os.path.join(MEMORY_DIR, "doi.txt")

    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f:
            for url in urls:
                # Extract DOI without the prefix
                doi = extract_doi(url)
                if doi:
                    f.write(f"{doi}\n")
    except IOError as e:
        logging.error(f"Error updating DOI memory file {filepath}: {e}")


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate articles by URL

    Ported from crawl.R:27

    Args:
        articles: List of article dictionaries

    Returns:
        Deduplicated list
    """
    seen_urls = set()
    unique_articles = []

    for article in articles:
        url = article.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_articles.append(article)

    return unique_articles


def remove_past_articles(
    articles: List[Dict[str, Any]],
    past_urls: Set[str]
) -> List[Dict[str, Any]]:
    """
    Filter out articles that have been previously crawled

    Ported from crawl.R:29

    Args:
        articles: List of article dictionaries
        past_urls: Set of previously seen DOIs (without prefix)

    Returns:
        Filtered list of new articles
    """
    return [
        article for article in articles
        if extract_doi(article.get("url")) not in past_urls
    ]


def clean_article_data(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean article data by stripping HTML and extracting DOIs

    Ported from crawl.R:38-41

    Args:
        articles: List of article dictionaries

    Returns:
        List with cleaned data
    """
    for article in articles:
        # Strip HTML from abstract
        if "abstract" in article:
            article["abstract"] = strip_html(article["abstract"])
            # Remove "Abstract" or "ABSTRACT" prefix
            if article["abstract"]:
                article["abstract"] = re.sub(
                    r'^(Abstract|ABSTRACT)\s+',
                    '',
                    article["abstract"]
                )

        # Strip HTML from title
        if "title" in article:
            article["title"] = strip_html(article["title"])

        # Extract DOI
        if "url" in article:
            article["doi"] = extract_doi(article["url"])

    return articles


def _find_journal_by_issn(issn_value: Any, journal_lookup: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Helper function to find journal by ISSN (handles both single ISSN and list of ISSNs)

    Args:
        issn_value: Single ISSN string or list of ISSN strings
        journal_lookup: Dictionary mapping ISSNs to journal data

    Returns:
        Journal dictionary if found, None otherwise
    """
    # Handle list of ISSNs
    if isinstance(issn_value, list):
        for issn in issn_value:
            if issn and issn in journal_lookup:
                return journal_lookup[issn]
        return None

    # Handle single ISSN string
    if issn_value and issn_value in journal_lookup:
        return journal_lookup[issn_value]

    return None


def merge_journal_info(
    articles: List[Dict[str, Any]],
    journals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge journal information into articles

    Args:
        articles: List of article dictionaries
        journals: List of journal dictionaries

    Returns:
        Articles with merged journal info
    """
    # Create lookup dictionaries by ISSN and EISSN
    journal_lookup = {}
    for j in journals:
        if j.get("issn"):
            journal_lookup[j["issn"]] = j
        if j.get("eissn"):
            journal_lookup[j["eissn"]] = j

    for article in articles:
        # Find journal using helper function
        journal = _find_journal_by_issn(article.get("issn"), journal_lookup)

        if journal:
            article["journal_id"] = journal.get("id", "")
            article["journal_name"] = journal.get("name", "")
            article["journal_eissn"] = journal.get("eissn", "")
            article["filters"] = journal.get("filter", [])
        else:
            article["journal_id"] = ""
            article["journal_name"] = ""
            article["journal_eissn"] = ""
            article["filters"] = []

    return articles


# OSF-specific processing functions
# Ported from picnic_preprints/crawl.R

def strip_whitespace(text: Optional[str]) -> Optional[str]:
    """
    Collapse multiple whitespaces and trim

    Ported from picnic_preprints/fun.R:56-62

    Args:
        text: Text with potential extra whitespace

    Returns:
        Cleaned text or None
    """
    if text is None:
        return None

    # Collapse multiple whitespaces
    text = re.sub(r'\s+', ' ', text)
    # Trim
    text = text.strip()

    return text if text else None




def load_past_osf_ids() -> Set[str]:
    """
    Load all previously crawled OSF preprint IDs from plain text file

    Returns:
        Set of OSF IDs (base IDs without version suffix)
    """
    filepath = os.path.join(MEMORY_DIR, "osf_ids.txt")

    if not os.path.exists(filepath):
        logging.warning(f"OSF ID memory file not found: {filepath}. Creating new one.")
        # Create empty file
        try:
            os.makedirs(MEMORY_DIR, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                pass  # Create empty file
        except IOError as e:
            logging.error(f"Error creating OSF ID memory file: {e}")
        return set()

    ids = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                id_value = line.strip()
                if id_value:
                    ids.add(id_value)
    except IOError as e:
        logging.error(f"Error reading OSF ID memory file {filepath}: {e}")

    return ids


def update_osf_id_memory(articles: List[Dict[str, Any]]) -> None:
    """
    Append new OSF IDs to memory file (plain text format)

    Args:
        articles: List of OSF article dictionaries with 'id' field
    """
    if not articles:
        return

    filepath = os.path.join(MEMORY_DIR, "osf_ids.txt")

    try:
        os.makedirs(MEMORY_DIR, exist_ok=True)

        # Extract unique IDs
        ids = set()
        for article in articles:
            osf_id = article.get("id")
            if osf_id:
                ids.add(osf_id)

        if not ids:
            return

        # Append to file
        with open(filepath, 'a', encoding='utf-8') as f:
            for osf_id in sorted(ids):
                f.write(f"{osf_id}\n")

    except IOError as e:
        logging.error(f"Error updating OSF ID memory file {filepath}: {e}")


def extract_osf_id_and_version(url: Optional[str]) -> Tuple[Optional[str], Optional[int]]:
    """
    Extract OSF ID and version from URL

    Ported from picnic_preprints/crawl.R:28-31

    Args:
        url: OSF preprint DOI URL

    Returns:
        Tuple of (id, version) where id is base ID without version suffix
    """
    if not url:
        return None, None

    try:
        # Get basename from URL (last part after /)
        # e.g., "https://doi.org/10.31219/osf.io/abc123_v2" -> "abc123_v2"
        id_version = url.rstrip('/').split('/')[-1]

        # Extract version number using regex
        version_match = re.search(r'_v([0-9]+)$', id_version)
        if version_match:
            version = int(version_match.group(1))
            # Remove version suffix to get base ID
            base_id = re.sub(r'_v[0-9]+$', '', id_version)
            return base_id, version
        else:
            # No version suffix, treat as version 1
            return id_version, 1

    except (ValueError, AttributeError, IndexError):
        return None, None


def deduplicate_osf_versions(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Keep only the latest version of each OSF preprint

    Ported from picnic_preprints/crawl.R:28-34

    Args:
        articles: List of OSF article dictionaries

    Returns:
        Deduplicated list with only latest versions
    """
    # Add id and version fields to each article
    for article in articles:
        osf_id, version = extract_osf_id_and_version(article.get("url"))
        article["id"] = osf_id
        article["version"] = version if version is not None else 1

    # Group by ID and keep max version
    id_groups = defaultdict(list)
    for article in articles:
        osf_id = article.get("id")
        if osf_id:
            id_groups[osf_id].append(article)

    # For each ID, keep only the article(s) with max version
    latest_articles = []
    for osf_id, group in id_groups.items():
        max_version = max(a.get("version", 1) for a in group)
        latest = [a for a in group if a.get("version", 1) == max_version]
        latest_articles.extend(latest)

    logging.info(f"Deduplicated OSF versions: {len(articles)} -> {len(latest_articles)}")
    return latest_articles


def remove_past_osf_preprints(
    articles: List[Dict[str, Any]],
    past_ids: Set[str]
) -> List[Dict[str, Any]]:
    """
    Filter out OSF preprints that have been previously crawled

    Ported from picnic_preprints/crawl.R:37

    Args:
        articles: List of OSF article dictionaries
        past_ids: Set of previously seen OSF IDs

    Returns:
        Filtered list of new preprints
    """
    return [
        article for article in articles
        if article.get("id") not in past_ids
    ]


def clean_osf_data(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean OSF article data

    Ported from picnic_preprints/crawl.R:39-42

    Args:
        articles: List of OSF article dictionaries

    Returns:
        List with cleaned data
    """
    for article in articles:
        # Strip whitespace from abstract
        if "abstract" in article:
            article["abstract"] = strip_whitespace(article["abstract"])

        # Strip whitespace from title
        if "title" in article:
            article["title"] = strip_whitespace(article["title"])

        # Extract DOI
        if "url" in article:
            article["doi"] = extract_doi(article["url"])

    return articles
