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


def load_osf_subject_filters() -> List[Dict[str, str]]:
    """
    Load OSF subject filter IDs from osf_subjects.json

    Returns:
        List of subject filter dictionaries with 'osf_id', 'osf_name', and 'osf_taxonomy' keys
        Returns empty list if file not found or error occurs
    """
    filepath = os.path.join(PARAMETERS_DIR, "osf_subjects.json")

    if not os.path.exists(filepath):
        logger.warning(f"OSF subjects file not found: {filepath}")
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            groups = data.get("groups", [])
            if groups:
                logger.info(f"Loaded {len(groups)} OSF subject filter(s)")
                for group in groups:
                    logger.info(f"  - {group.get('osf_name')} ({group.get('osf_taxonomy')}): {group.get('osf_id')}")
            return groups
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Error loading OSF subjects file {filepath}: {e}")
        return []


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

    # Load subject filters from osf_subjects.json
    subject_filters = load_osf_subject_filters()
    if not subject_filters:
        logger.error("No OSF subject filters found. Please run make_osf_subjects.py first.")
        return []

    session = create_osf_session()
    all_items = []
    seen_ids = set()  # Track unique preprint IDs to avoid duplicates

    # Generate date range
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        logger.info(f"Processing OSF preprints for {date_str}")

        # Iterate through all subject filters
        for subject_filter in subject_filters:
            subject_id = subject_filter.get("osf_id")
            subject_name = subject_filter.get("osf_name")
            subject_taxonomy = subject_filter.get("osf_taxonomy")

            logger.info(f"  Using filter: {subject_name} ({subject_taxonomy})")

            try:
                # Get first page to determine total pages
                first_response = call_osf_api(session, date_str, subject_id, page=1)
                total_pages = get_total_pages(first_response)

                if total_pages == 0:
                    logger.info(f"  No preprints found for {date_str} with {subject_taxonomy}")
                    continue

                logger.info(f"  Found {total_pages} page(s) for {date_str} with {subject_taxonomy}")

                # Collect items from all pages
                for page in range(1, total_pages + 1):
                    if page == 1:
                        # Use first response we already fetched
                        response = first_response
                    else:
                        response = call_osf_api(session, date_str, subject_id, page=page)

                    items = response.get("data", [])

                    # Filter out duplicates based on preprint ID
                    for item in items:
                        item_id = item.get("id")
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            all_items.append(item)

                    logger.debug(f"  Retrieved {len(items)} items from page {page}/{total_pages}")

            except requests.RequestException as e:
                logger.error(f"  Error retrieving preprints for {date_str} with {subject_taxonomy}: {e}")

        # Move to next day
        current_date = current_date + timedelta(days=1)

    logger.info(f"Retrieved total of {len(all_items)} unique preprint items")
    return all_items
