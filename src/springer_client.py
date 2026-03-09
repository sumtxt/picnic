"""
Springer Nature Meta API client for fetching article metadata

Queries the Springer Meta API in JATS format to retrieve article_type metadata.
Used by the "nature2" filter to identify OriginalArticle and ReviewPaper types.

Batches DOIs in groups of 25 for efficient API usage with retry logic for
incomplete responses.
"""

import logging
import time
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from lxml import etree

from .config import (
    SPRINGER_API_KEY,
    SPRINGER_API_BASE,
    SPRINGER_BATCH_SIZE,
    SPRINGER_BATCH_DELAY,
    SPRINGER_MAX_RETRIES,
    SPRINGER_RETRY_BACKOFF,
    SPRINGER_TIMEOUT,
)


def create_springer_session() -> requests.Session:
    """
    Create a requests Session with retry logic for Springer API calls.

    Uses the same pattern as crossref_client.py and osf_client.py.

    Returns:
        Configured requests.Session with retry strategy
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=SPRINGER_RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def get_text_content(elem) -> str:
    """Get all text content from an XML element, including nested elements."""
    return ''.join(elem.itertext())


def parse_jats_article(article_elem) -> Dict[str, str]:
    """
    Parse a single <article> element from JATS XML.

    Returns dict with doi, article_type, and auto_keywords.
    """
    result = {
        'doi': '',
        'article_type': '',
        'auto_keywords': '',
    }

    front = article_elem.find('front')
    if front is None:
        return result

    article_meta = front.find('article-meta')
    if article_meta is None:
        return result

    # Extract DOI
    for article_id in article_meta.findall('article-id'):
        if article_id.get('pub-id-type') == 'doi':
            result['doi'] = (article_id.text or '').strip()
            break

    # Extract auto-generated keywords
    for kwd_group in article_meta.findall('kwd-group'):
        if kwd_group.get('kwd-group-type') == 'publisher-auto-generated':
            keywords = []
            for kwd in kwd_group.findall('kwd'):
                kwd_text = get_text_content(kwd).strip()
                if kwd_text:
                    keywords.append(kwd_text)
            result['auto_keywords'] = '; '.join(keywords)
            break

    # Extract article-type from custom-meta-group
    custom_meta_group = article_meta.find('custom-meta-group')
    if custom_meta_group is not None:
        for custom_meta in custom_meta_group.findall('custom-meta'):
            meta_name = custom_meta.find('meta-name')
            meta_value = custom_meta.find('meta-value')
            if meta_name is not None and meta_value is not None:
                name_text = (meta_name.text or '').strip()
                if name_text == 'article-type':
                    result['article_type'] = (meta_value.text or '').strip()
                    break

    return result


def fetch_batch_jats(
    session: requests.Session,
    dois: List[str]
) -> Dict[str, Dict[str, str]]:
    """
    Fetch metadata for a batch of DOIs in JATS format.

    Args:
        session: requests.Session with configured retry logic
        dois: List of DOIs to fetch (max 25 recommended)

    Returns:
        Dict mapping DOI -> metadata dict
    """
    if not dois:
        return {}

    # Build OR query
    doi_queries = [f'doi:"{doi}"' for doi in dois]
    query = "(" + " OR ".join(doi_queries) + ")"

    params = {
        'api_key': SPRINGER_API_KEY,
        'q': query,
        'p': SPRINGER_BATCH_SIZE,
        's': 1,
    }

    try:
        response = session.get(SPRINGER_API_BASE, params=params, timeout=SPRINGER_TIMEOUT)
        response.raise_for_status()

        # Parse XML response with lxml
        parser = etree.XMLParser(recover=True, resolve_entities=False)
        root = etree.fromstring(response.content, parser)

        # Find all article elements in records
        records = root.find('records')
        if records is None:
            return {}

        results = {}
        for article in records.findall('article'):
            parsed = parse_jats_article(article)
            if parsed['doi']:
                results[parsed['doi']] = parsed

        return results

    except requests.RequestException as e:
        logging.error(f"Springer API request error: {e}")
        return {}
    except etree.XMLSyntaxError as e:
        logging.error(f"Springer API XML parse error: {e}")
        return {}
    except Exception as e:
        logging.error(f"Springer API error fetching batch: {e}")
        return {}


def fetch_springer_metadata_with_retry(
    dois: List[str],
    batch_delay: float = SPRINGER_BATCH_DELAY,
    max_retries: int = SPRINGER_MAX_RETRIES
) -> Dict[str, Dict[str, str]]:
    """
    Fetch Springer metadata for a list of DOIs with batching and retry logic.

    Processes DOIs in batches of SPRINGER_BATCH_SIZE (25). If the API returns
    fewer results than requested, the missing DOIs are collected and retried
    in subsequent rounds up to max_retries times.

    Args:
        dois: List of DOIs to fetch metadata for
        batch_delay: Seconds to wait between batch API calls
        max_retries: Maximum number of retry rounds for missing DOIs

    Returns:
        Dict mapping DOI -> metadata dict for all successfully fetched DOIs
    """
    if not dois:
        return {}

    session = create_springer_session()
    all_results: Dict[str, Dict[str, str]] = {}
    remaining_dois = list(dois)

    total_batches = (len(dois) + SPRINGER_BATCH_SIZE - 1) // SPRINGER_BATCH_SIZE
    logging.info(f"Fetching Springer metadata for {len(dois)} DOIs in {total_batches} batches")

    retry_round = 0

    while remaining_dois and retry_round <= max_retries:
        if retry_round > 0:
            logging.info(f"Retry round {retry_round}/{max_retries}: {len(remaining_dois)} missing DOIs")

        batches = [
            remaining_dois[i:i + SPRINGER_BATCH_SIZE]
            for i in range(0, len(remaining_dois), SPRINGER_BATCH_SIZE)
        ]

        newly_missing = []

        for batch_idx, batch_dois in enumerate(batches, 1):
            logging.info(
                f"Batch {batch_idx}/{len(batches)}: fetching {len(batch_dois)} DOIs..."
            )

            results = fetch_batch_jats(session, batch_dois)

            # Track results
            found_count = len(results)
            logging.info(f"Batch {batch_idx}/{len(batches)}: received {found_count}/{len(batch_dois)} results")

            all_results.update(results)

            # Track missing DOIs for retry
            for doi in batch_dois:
                if doi not in results:
                    newly_missing.append(doi)

            # Polite delay between batches (skip after last batch)
            if batch_idx < len(batches):
                time.sleep(batch_delay)

        remaining_dois = newly_missing
        retry_round += 1

        # Delay before retry round
        if remaining_dois and retry_round <= max_retries:
            logging.info(f"Waiting {batch_delay}s before retry round...")
            time.sleep(batch_delay)

    if remaining_dois:
        logging.warning(
            f"Could not fetch metadata for {len(remaining_dois)} DOIs after {max_retries} retries"
        )

    logging.info(f"Springer metadata fetch complete: {len(all_results)}/{len(dois)} DOIs retrieved")
    return all_results
