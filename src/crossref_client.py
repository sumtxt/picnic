"""
Crossref API client for retrieving article metadata

Ported from fun.R:157-309
"""

import logging
import time
import random
from typing import Optional, Dict, Any
from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    CROSSREF_API_BASE,
    CROSSREF_EMAIL,
    CROSSREF_TIMEOUT,
    CROSSREF_ROWS,
    CROSSREF_RETRY_BACKOFF
)


def create_session(polite_email: Optional[str] = None) -> requests.Session:
    """
    Create a requests Session with retry logic and optional polite pooling

    Args:
        polite_email: Email for polite pool access (faster response times)

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    # Configure retry strategy (equivalent to R's httr::RETRY with pause_base=5)
    retry_strategy = Retry(
        total=5,
        backoff_factor=CROSSREF_RETRY_BACKOFF,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Add polite pool email if provided
    if polite_email:
        session.params = {"mailto": polite_email}

    return session


def call_crossref_api(
    issn: str,
    start_date: date,
    end_date: date,
    date_type: str,
    session: requests.Session
) -> Optional[Dict[str, Any]]:
    """
    Call Crossref API for a specific ISSN and date range

    Ported from fun.R:157-181

    Args:
        issn: Journal ISSN
        start_date: Start of date range
        end_date: End of date range
        date_type: Either "created" or "published"
        session: requests.Session with configured retry logic

    Returns:
        API response as dict, or None on error
    """
    if date_type not in ["created", "published"]:
        logging.error(f"Invalid date_type: {date_type}. Must be 'created' or 'published'")
        return None

    # Build endpoint URL
    endpoint = f"{CROSSREF_API_BASE}/journals/{issn}/works"

    # Build filter parameter
    if date_type == "created":
        filter_param = f"from-created-date:{start_date},until-created-date:{end_date}"
    else:  # published
        filter_param = f"from-pub-date:{start_date},until-pub-date:{end_date}"

    # Build query parameters
    params = {
        "filter": filter_param,
        "select": "title,author,abstract,URL,created",
        "rows": CROSSREF_ROWS
    }

    try:
        response = session.get(endpoint, params=params, timeout=CROSSREF_TIMEOUT)
        response.raise_for_status()

        # Log rate limit information
        rate_limit = response.headers.get("x-ratelimit-limit")
        rate_interval = response.headers.get("x-ratelimit-interval")
        if rate_limit and rate_interval:
            logging.debug(f"Rate limit: {rate_limit}/{rate_interval}")

        return response.json()

    except requests.exceptions.Timeout:
        logging.error(f"Timeout for ISSN {issn} ({date_type})")
        return None

    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error for ISSN {issn} ({date_type}): {e}")
        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for ISSN {issn} ({date_type}): {e}")
        return None

    except ValueError as e:  # JSON decode error
        logging.error(f"Invalid JSON for ISSN {issn} ({date_type}): {e}")
        return None


def test_endpoint_speed(
    start_date: date,
    end_date: date,
    timeout: int
) -> int:
    """
    Test response times for public vs polite Crossref endpoints using bulk approach

    Tests the /works endpoint with multiple ISSNs to match the bulk retrieval method.

    Args:
        start_date: Start of date range
        end_date: End of date range
        timeout: Timeout in seconds

    Returns:
        0 if both failed
        1 if public is faster
        2 if polite is faster
    """
    # Sample ISSNs 
    sample_issns = [
        "1476-4989",
        "0048-5829",
        "1554-0626",
        "0010-4159",
        "1460-3667",
        "0962-6298",
        "0043-8871",
        "1545-1577",
        "0140-2382",
        "1743-9655",
        "0020-8833",
        "1047-1987",
        "0362-9805",
        "1537-5943",
        "1469-2112",
    ]
    # Use a random subset to test the bulk endpoint (reduces API load)
    test_issns = random.sample(sample_issns, min(3, len(sample_issns)))

    # Use /works endpoint with ISSN filter (bulk approach)
    url = f"{CROSSREF_API_BASE}/works"

    # Build ISSN filter
    issn_filter = ",".join([f"issn:{issn}" for issn in test_issns])
    date_filter = f"from-created-date:{start_date},until-created-date:{end_date}"
    filter_param = f"{issn_filter},{date_filter}"

    params = {
        "filter": filter_param,
        "select": "title,author,abstract,URL,created,ISSN,container-title",
        "rows": CROSSREF_ROWS,
        "cursor": "*"
    }

    # Test public endpoint
    result1_time = None
    result1_success = False

    try:
        start_time = time.time()
        response = requests.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        result1_time = time.time() - start_time
        result1_success = True
    except Exception as e:
        logging.debug(f"Public endpoint test failed: {e}")

    # Test polite endpoint
    result2_time = None
    result2_success = False

    params_polite = params.copy()
    params_polite["mailto"] = CROSSREF_EMAIL

    try:
        start_time = time.time()
        response = requests.get(url, params=params_polite, timeout=timeout)
        response.raise_for_status()
        result2_time = time.time() - start_time
        result2_success = True
    except Exception as e:
        logging.debug(f"Polite endpoint test failed: {e}")

    # Log results
    if result1_success:
        logging.info(f"\tPublic API response time: {result1_time:.2f} seconds")
    if result2_success:
        logging.info(f"\tPolite API response time: {result2_time:.2f} seconds")

    # Determine which endpoint to use
    if result1_success and not result2_success:
        return 1
    elif not result1_success and result2_success:
        return 2
    elif not result1_success and not result2_success:
        return 0
    else:
        return 1 if result1_time < result2_time else 2


def select_best_endpoint(start_date: date, end_date: date) -> bool:
    """
    Test Crossref endpoints and select the faster one

    Ported from fun.R:299-309

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        True to use polite endpoint, False to use public endpoint
    """
    MAX_TIMEOUT = 60  # Maximum timeout in seconds
    result = 0
    timeout = 1

    while result == 0 and timeout <= MAX_TIMEOUT:
        logging.info(f"Testing Crossref API with timeout: {timeout} seconds")
        result = test_endpoint_speed(start_date, end_date, timeout)

        if result != 0:
            break

        timeout += 5

    # If both endpoints failed, default to polite endpoint
    if result == 0:
        logging.warning(f"Both endpoints failed after {MAX_TIMEOUT}s timeout. Defaulting to polite endpoint.")
        return True

    # result == 2 means polite is faster
    return result == 2


def call_crossref_api_with_issn_filter(
    issn_list: list,
    start_date: date,
    end_date: date,
    date_type: str,
    session: requests.Session,
    verbose: bool = False
) -> list:
    """
    Call Crossref API using /works endpoint with ISSN filter

    Uses cursor-based pagination to handle large result sets (>1000 items).
    Ported from paper-picnic-fun=updated.R:151-178

    Args:
        issn_list: List of journal ISSNs
        start_date: Start of date range
        end_date: End of date range
        date_type: Either "created" or "published"
        session: requests.Session with configured retry logic
        verbose: Whether to log progress

    Returns:
        List of article items from all pages
    """
    if date_type not in ["created", "published"]:
        logging.error(f"Invalid date_type: {date_type}. Must be 'created' or 'published'")
        return []

    # Build endpoint URL - use /works instead of /journals/{issn}/works
    endpoint = f"{CROSSREF_API_BASE}/works"

    # Build filter parameter with ISSN list
    # Format: issn:1234-5678,issn:5678-1234,...
    issn_filter = ",".join([f"issn:{issn}" for issn in issn_list])

    # Build date filter
    if date_type == "created":
        date_filter = f"from-created-date:{start_date},until-created-date:{end_date}"
    else:  # published
        date_filter = f"from-pub-date:{start_date},until-pub-date:{end_date}"

    # Combine filters
    filter_param = f"{issn_filter},{date_filter}"

    # Build query parameters
    params = {
        "filter": filter_param,
        "select": "title,author,abstract,URL,created,ISSN,container-title",
        "rows": CROSSREF_ROWS,
        "cursor": "*"  # Initialize cursor for deep paging
    }

    all_items = []
    page_count = 0

    while True:
        page_count += 1

        try:
            response = session.get(endpoint, params=params, timeout=CROSSREF_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            # Log rate limit information
            rate_limit = response.headers.get("x-ratelimit-limit")
            rate_interval = response.headers.get("x-ratelimit-interval")
            if rate_limit and rate_interval:
                logging.debug(f"Rate limit: {rate_limit}/{rate_interval}")

            # Extract items
            if "message" in data and "items" in data["message"]:
                items = data["message"]["items"]
                total_results = data["message"].get("total-results", 0)
                all_items.extend(items)

                if verbose:
                    logging.info(f"Page {page_count}: Retrieved {len(items)} items (total: {len(all_items)}/{total_results})")

                # Check if there are no more items on this page
                if len(items) == 0:
                    logging.info("No items in response, stopping pagination")
                    break

                # Check if we've retrieved all results
                if len(all_items) >= total_results:
                    if verbose:
                        logging.info(f"Retrieved all {total_results} results, stopping pagination")
                    break

                # Check if there's a next cursor
                if "next-cursor" in data["message"]:
                    next_cursor = data["message"]["next-cursor"]
                    params["cursor"] = next_cursor
                else:
                    # No more pages
                    break
            else:
                # No items found
                break

        except requests.exceptions.Timeout:
            logging.error(f"Timeout on page {page_count} ({date_type})")
            break

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error on page {page_count} ({date_type}): {e}")
            break

        except requests.exceptions.RequestException as e:
            logging.error(f"Request error on page {page_count} ({date_type}): {e}")
            break

        except ValueError as e:  # JSON decode error
            logging.error(f"Invalid JSON on page {page_count} ({date_type}): {e}")
            break

    return all_items


def retrieve_crossref_issn_data(
    issn_list: list,
    start_date: date,
    end_date: date,
    verbose: bool = False,
    polite_endpoint: bool = True
) -> list:
    """
    Retrieve article data from Crossref for multiple ISSNs

    Ported from fun.R:4-36

    Args:
        issn_list: List of journal ISSNs
        start_date: Start of date range
        end_date: End of date range
        verbose: Whether to log progress
        polite_endpoint: Whether to use polite endpoint

    Returns:
        List of article dictionaries
    """
    # Create session
    email = CROSSREF_EMAIL if polite_endpoint else None
    session = create_session(polite_email=email)

    all_articles = []

    for issn in issn_list:
        if verbose:
            logging.info(f"Processing ISSN: {issn}")

        # Query both created and published dates
        for date_type in ["created", "published"]:
            data = call_crossref_api(issn, start_date, end_date, date_type, session)

            if data and "message" in data and "items" in data["message"]:
                # Parse articles (will be done by parsers module)
                items = data["message"]["items"]
                for item in items:
                    # Add ISSN to each item for later reference
                    item["_issn"] = issn
                    all_articles.append(item)

    return all_articles


def retrieve_crossref_issn_data_bulk(
    issn_list: list,
    start_date: date,
    end_date: date,
    verbose: bool = False,
    polite_endpoint: bool = True,
    batch_size: int = 50
) -> list:
    """
    Retrieve article data from Crossref using bulk ISSN filter approach

    This implementation uses the /works endpoint with multiple ISSNs in a single filter,
    rather than querying each journal separately. Uses cursor-based pagination to
    handle result sets larger than 1000 items.

    To avoid HTTP 414 errors (Request-URI Too Large), ISSNs are processed in batches.

    Ported from paper-picnic-fun=updated.R:4-30

    Args:
        issn_list: List of journal ISSNs
        start_date: Start of date range
        end_date: End of date range
        verbose: Whether to log progress
        polite_endpoint: Whether to use polite endpoint
        batch_size: Number of ISSNs to include per request (default: 50)

    Returns:
        List of article dictionaries
    """
    # Create session
    email = CROSSREF_EMAIL if polite_endpoint else None
    session = create_session(polite_email=email)

    all_articles = []

    # Split ISSNs into batches to avoid URL length limits (HTTP 414 errors)
    issn_batches = [issn_list[i:i + batch_size] for i in range(0, len(issn_list), batch_size)]

    if verbose:
        logging.info(f"Processing {len(issn_list)} ISSNs in {len(issn_batches)} batches of up to {batch_size}")

    # Query both created and published dates
    for date_type in ["created", "published"]:
        if verbose:
            logging.info(f"Querying {date_type} dates...")

        for batch_idx, issn_batch in enumerate(issn_batches, 1):
            if verbose:
                logging.info(f"  Batch {batch_idx}/{len(issn_batches)}: Processing {len(issn_batch)} ISSNs")

            items = call_crossref_api_with_issn_filter(
                issn_list=issn_batch,
                start_date=start_date,
                end_date=end_date,
                date_type=date_type,
                session=session,
                verbose=verbose
            )

            all_articles.extend(items)

    return all_articles
