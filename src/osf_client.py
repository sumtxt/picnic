"""
OSF API client for retrieving preprints
"""

import logging
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    OSF_API_BASE,
    OSF_TIMEOUT,
    PARAMETERS_DIR,
)

logger = logging.getLogger(__name__)


def load_osf_subject_filter() -> Optional[str]:
    """
    Load OSF subject filter ID from osf_subjects.json

    Returns:
        Subject filter ID or None if file not found
    """
    filepath = os.path.join(PARAMETERS_DIR, "osf_subjects.json")

    if not os.path.exists(filepath):
        logger.warning(f"OSF subjects file not found: {filepath}")
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            category_id = data.get("category_id")
            if category_id:
                logger.info(f"Loaded OSF subject filter: {category_id} ({data.get('category_name', 'Unknown')})")
            return category_id
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading OSF subjects file {filepath}: {e}")
        return None


def create_osf_session() -> requests.Session:
    """
    Create a requests Session with retry logic for OSF API calls.

    Returns:
        Configured requests.Session with retry strategy
    """
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def call_osf_api(session: requests.Session, date: str, subject_filter: str, page: int = 1) -> Dict[str, Any]:
    """
    Call OSF API for preprints on a specific date and page.

    Args:
        session: requests.Session object
        date: Date in YYYY-MM-DD format
        subject_filter: OSF subject filter ID
        page: Page number (default: 1)

    Returns:
        JSON response from OSF API

    Raises:
        requests.RequestException: If API call fails
    """
    endpoint = f"{OSF_API_BASE}/preprints/"

    params = {
        "filter[subjects]": subject_filter,
        "filter[date_published]": date,
        "fields[preprints]": "title,description,date_created,contributors,subjects",
        "embed": "contributors",
        "fields[users]": "full_name",
        "format": "jsonapi",
        "page": page
    }

    logger.debug(f"Calling OSF API for date={date}, page={page}")

    response = session.get(endpoint, params=params, timeout=OSF_TIMEOUT)
    response.raise_for_status()

    return response.json()


def get_total_pages(data: Dict[str, Any]) -> int:
    """
    Calculate total number of pages from OSF API response.

    Args:
        data: OSF API response JSON

    Returns:
        Total number of pages
    """
    try:
        total = data["links"]["meta"]["total"]
        per_page = data["links"]["meta"]["per_page"]
        total_pages = (total + per_page - 1) // per_page  # Ceiling division
        return total_pages
    except (KeyError, TypeError, ZeroDivisionError):
        logger.warning("Could not determine total pages, returning 0")
        return 0


def retrieve_osf_preprints(start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
    """
    Retrieve all OSF preprints within a date range.

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        List of preprint items from OSF API
    """
    from datetime import timedelta

    logger.info(f"Retrieving OSF preprints from {start_date.date()} to {end_date.date()}")

    # Load subject filter from osf_subjects.json
    subject_filter = load_osf_subject_filter()
    if not subject_filter:
        logger.error("No OSF subject filter found. Please run make_osf_subjects.py first.")
        return []

    session = create_osf_session()
    all_items = []

    # Generate date range
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        logger.info(f"Processing OSF preprints for {date_str}")

        try:
            # Get first page to determine total pages
            first_response = call_osf_api(session, date_str, subject_filter, page=1)
            total_pages = get_total_pages(first_response)

            if total_pages == 0:
                logger.info(f"No preprints found for {date_str}")
                current_date = current_date + timedelta(days=1)
                continue

            logger.info(f"Found {total_pages} page(s) for {date_str}")

            # Collect items from all pages
            for page in range(1, total_pages + 1):
                if page == 1:
                    # Use first response we already fetched
                    response = first_response
                else:
                    response = call_osf_api(session, date_str, subject_filter, page=page)

                items = response.get("data", [])
                all_items.extend(items)
                logger.debug(f"Retrieved {len(items)} items from page {page}/{total_pages}")

        except requests.RequestException as e:
            logger.error(f"Error retrieving preprints for {date_str}: {e}")

        # Move to next day
        current_date = current_date + timedelta(days=1)

    logger.info(f"Retrieved total of {len(all_items)} preprint items")
    return all_items
