"""
OpenAlex API client for domain-based filtering

Queries the OpenAlex API to retrieve article domain classification.
Used to filter out articles that are not in the Social Sciences domain.
"""

import logging
import time
import requests
from typing import Optional

from .config import (
    OPENALEX_API_KEY,
    OPENALEX_API_BASE,
    OPENALEX_TIMEOUT,
    OPENALEX_BATCH_SIZE,
    CROSSREF_EMAIL,
    CROSSREF_RETRY_BACKOFF,
)

# Maximum retry attempts for API calls
MAX_RETRIES = 5


def query_openalex_batch(
    dois: list[str],
    max_retries: int = MAX_RETRIES,
    backoff_factor: int = CROSSREF_RETRY_BACKOFF,
) -> dict[str, Optional[str]]:
    """
    Query OpenAlex API for multiple DOIs in a single batch request.

    Uses exponential backoff for retries on timeout or server errors.
    Backoff times: 5s, 10s, 20s, 40s, 80s

    Args:
        dois: List of DOI URLs (e.g., ["https://doi.org/10.1073/pnas.XXX", ...])
              Maximum 50 DOIs per batch.
        max_retries: Maximum number of retry attempts (default: 5)
        backoff_factor: Exponential backoff factor (default: 5 from config)

    Returns:
        Dictionary mapping DOI -> domain_name (or None if not found/error)
    """
    if not dois:
        return {}

    if len(dois) > OPENALEX_BATCH_SIZE:
        logging.warning(
            f"Batch size {len(dois)} exceeds limit {OPENALEX_BATCH_SIZE}, truncating"
        )
        dois = dois[:OPENALEX_BATCH_SIZE]

    # Normalize DOIs (remove https://doi.org/ prefix if present)
    doi_values = [doi.replace("https://doi.org/", "") for doi in dois]
    doi_filter = "|".join(doi_values)

    params = {
        "filter": f"doi:{doi_filter}",
        "per-page": len(dois),
        "select": "doi,primary_topic",
    }

    # Add API key if available
    if OPENALEX_API_KEY:
        params["api_key"] = OPENALEX_API_KEY

    # Add email for polite pool
    if CROSSREF_EMAIL:
        params["mailto"] = CROSSREF_EMAIL

    # Retry loop with exponential backoff
    for attempt in range(max_retries):
        try:
            response = requests.get(
                OPENALEX_API_BASE, params=params, timeout=OPENALEX_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                # Build mapping of DOI -> domain_name
                doi_to_domain = {}
                for work in results:
                    work_doi = work.get("doi", "")
                    if work_doi:
                        # Normalize the DOI from OpenAlex response
                        work_doi_normalized = work_doi.replace("https://doi.org/", "")

                        # Extract domain_name from primary_topic
                        primary_topic = work.get("primary_topic") or {}
                        domain = primary_topic.get("domain") or {}
                        domain_name = domain.get("display_name")

                        doi_to_domain[work_doi_normalized] = domain_name

                # Map back to original DOIs, returning None for DOIs not found
                result = {}
                for doi in dois:
                    doi_normalized = doi.replace("https://doi.org/", "")
                    result[doi] = doi_to_domain.get(doi_normalized)

                return result

            elif response.status_code == 429:
                # Rate limit hit
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2**attempt)
                    logging.warning(
                        f"OpenAlex rate limit hit. "
                        f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(
                        f"OpenAlex rate limit exceeded after {max_retries} attempts"
                    )
                    return {doi: None for doi in dois}

            elif response.status_code >= 500:
                # Server error - retry with backoff
                if attempt < max_retries - 1:
                    wait_time = backoff_factor * (2**attempt)
                    logging.warning(
                        f"OpenAlex server error (HTTP {response.status_code}). "
                        f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logging.error(
                        f"OpenAlex server error after {max_retries} attempts: "
                        f"HTTP {response.status_code}"
                    )
                    return {doi: None for doi in dois}

            else:
                # Client error (4xx except 429) - don't retry
                logging.error(
                    f"OpenAlex API error: HTTP {response.status_code} - "
                    f"{response.text[:200]}"
                )
                return {doi: None for doi in dois}

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = backoff_factor * (2**attempt)
                logging.warning(
                    f"OpenAlex API timeout. "
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logging.error(f"OpenAlex API timeout after {max_retries} attempts")
                return {doi: None for doi in dois}

        except requests.exceptions.RequestException as e:
            # Network errors - retry with backoff
            if attempt < max_retries - 1:
                wait_time = backoff_factor * (2**attempt)
                logging.warning(
                    f"OpenAlex request error: {e}. "
                    f"Retry {attempt + 1}/{max_retries} after {wait_time}s..."
                )
                time.sleep(wait_time)
            else:
                logging.error(
                    f"OpenAlex API request error after {max_retries} attempts: {e}"
                )
                return {doi: None for doi in dois}

    # Should not reach here, but just in case
    return {doi: None for doi in dois}


def query_openalex_all(dois: list[str]) -> dict[str, Optional[str]]:
    """
    Query OpenAlex API for all DOIs, batching automatically.

    Args:
        dois: List of DOI URLs (any length)

    Returns:
        Dictionary mapping DOI -> domain_name (or None if not found/error)
    """
    if not dois:
        return {}

    all_results = {}
    total_batches = (len(dois) + OPENALEX_BATCH_SIZE - 1) // OPENALEX_BATCH_SIZE

    for batch_num in range(total_batches):
        start_idx = batch_num * OPENALEX_BATCH_SIZE
        end_idx = min(start_idx + OPENALEX_BATCH_SIZE, len(dois))
        batch_dois = dois[start_idx:end_idx]

        logging.info(
            f"OpenAlex batch {batch_num + 1}/{total_batches}: "
            f"querying {len(batch_dois)} DOIs"
        )

        batch_results = query_openalex_batch(batch_dois)
        all_results.update(batch_results)

        # Small delay between batches to be polite to the API
        if batch_num < total_batches - 1:
            time.sleep(0.1)

    return all_results
