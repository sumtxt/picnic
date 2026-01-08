#!/usr/bin/env python3
"""
Main crawl script for Paper Picnic

Ported from crawl.R
"""

import sys
import logging
import os
from datetime import datetime, timedelta, timezone

from src.config import (
    CRAWL_WINDOW_START,
    CRAWL_WINDOW_END,
    OUTPUT_DIR,
    LOGS_DIR,
    UPDATE_MEMORY,
    UPDATE_STATS,
    LIMIT_JOURNALS,
    ENABLE_CROSSREF_CRAWL,
    ENABLE_OSF_CRAWL
)
from src.crossref_client import select_best_endpoint, retrieve_crossref_issn_data_bulk
from src.osf_client import retrieve_osf_preprints
from src.parsers import parse_crossref_response, parse_osf_response
from src.data_processor import (
    load_journals,
    load_past_dois,
    deduplicate_articles,
    remove_past_articles,
    clean_article_data,
    merge_journal_info,
    update_doi_memory,
    load_past_osf_ids,
    deduplicate_osf_versions,
    remove_past_osf_preprints,
    clean_osf_data,
    update_osf_id_memory
)
from src.filters import apply_all_filters
from src.json_renderer import render_json_by_journal, render_osf_json
from src.stats_updater import update_stats_csv


def setup_logging() -> None:
    """Configure logging for the crawl"""
    handlers = []

    # In GitHub Actions, only log to console
    if os.environ.get("GITHUB_ACTIONS") == "true":
        handlers.append(logging.StreamHandler())
    else:
        # When running locally, log to both file and console
        os.makedirs(LOGS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(LOGS_DIR, f"crawl_{timestamp}.log")
        handlers.extend([
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ])

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers
    )

    logging.info("Starting Paper Picnic crawl")


def main():
    """Main crawl function"""
    # Setup logging
    setup_logging()

    # Calculate crawl date range (UTC)
    now = datetime.now(timezone.utc)

    # Check if at least one crawler is enabled
    if not ENABLE_CROSSREF_CRAWL and not ENABLE_OSF_CRAWL:
        logging.error("Both ENABLE_CROSSREF_CRAWL and ENABLE_OSF_CRAWL are disabled. At least one must be enabled.")
        sys.exit(1)

    # Crossref Crawl
    if ENABLE_CROSSREF_CRAWL:
        logging.info("="*50)
        logging.info("Starting Crossref journal crawl...")
        logging.info("="*50)

        crawl_start_date = (now - timedelta(days=CRAWL_WINDOW_START)).date()
        crawl_end_date = (now - timedelta(days=CRAWL_WINDOW_END)).date()

        logging.info(f"Crawl window: {crawl_start_date} to {crawl_end_date}")

        # Load journals configuration
        journals = load_journals()
        if not journals:
            logging.error("No journals found in journals.json")
            sys.exit(1)

        # Apply journal limit if configured
        if LIMIT_JOURNALS is not None and LIMIT_JOURNALS > 0:
            original_count = len(journals)
            journals = journals[:LIMIT_JOURNALS]
            logging.info(f"Loaded {len(journals)} journals (limited from {original_count})")
        else:
            logging.info(f"Loaded {len(journals)} journals")

        # Load past DOIs
        past_dois = load_past_dois()
        logging.info(f"Loaded {len(past_dois)} past DOIs")

        # Test Crossref endpoints to find fastest
        use_polite = select_best_endpoint(crawl_start_date, crawl_end_date)
        logging.info(f"Using polite endpoint: {use_polite}")

        # Retrieve articles from Crossref API using bulk approach
        logging.info("Retrieving articles from Crossref API (bulk approach)...")
        # Some journals might have only ISSN or only EISSN, handle both
        issn_list = []
        for j in journals:
            if j.get("issn"):
                issn_list.append(j["issn"])
            if j.get("eissn"):
                issn_list.append(j["eissn"])

        # Deduplicate ISSN list
        issn_list = list(set(issn_list))

        raw_items = retrieve_crossref_issn_data_bulk(
            issn_list=issn_list,
            start_date=crawl_start_date,
            end_date=crawl_end_date,
            verbose=True,
            polite_endpoint=use_polite
        )

        logging.info(f"Retrieved {len(raw_items)} raw items from Crossref")

        # Parse articles
        articles = parse_crossref_response(raw_items)
        logging.info(f"Parsed {len(articles)} articles")

        # Remove duplicates
        articles = deduplicate_articles(articles)
        logging.info(f"After deduplication: {len(articles)} articles")

        # Remove past articles
        articles = remove_past_articles(articles, past_dois)
        logging.info(f"After removing past articles: {len(articles)} new articles")

        # Check if we have any articles
        if articles:
            # Clean article data (strip HTML, extract DOIs)
            articles = clean_article_data(articles)
            logging.info("Cleaned article data")

            # Merge journal information
            articles = merge_journal_info(articles, journals)
            logging.info("Merged journal information")

            # Apply filters
            logging.info("Applying filters...")
            articles = apply_all_filters(articles)

            # Count filtered articles
            visible_count = sum(1 for a in articles if a.get("filter", 0) in [0, -1])
            hidden_count = sum(1 for a in articles if a.get("filter", 0) not in [0, -1])
            logging.info(f"Filtered: {visible_count} visible, {hidden_count} hidden")

            # Render JSON by journal into single file
            json_content = render_json_by_journal(articles, now.date())

            # Write output to single publications.json file
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            output_path = os.path.join(OUTPUT_DIR, "publications.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            logging.info(f"Output written to: {output_path}")

            # Update DOI memory
            if UPDATE_MEMORY:
                new_urls = [a["url"] for a in articles if a.get("url")]
                update_doi_memory(new_urls)
                logging.info(f"Updated DOI memory with {len(new_urls)} DOIs")
            else:
                logging.info("DOI memory update disabled in config")
        else:
            logging.info("No new Crossref articles found.")
    else:
        logging.info("Crossref crawl disabled in config (ENABLE_CROSSREF_CRAWL=False)")

    # OSF Preprints Workflow
    if ENABLE_OSF_CRAWL:
        logging.info("\n" + "="*50)
        logging.info("Starting OSF preprints crawl...")
        logging.info("="*50)

        # Calculate OSF crawl date range (using same window as Crossref per user request)
        osf_start_date = now - timedelta(days=CRAWL_WINDOW_START)
        osf_end_date = now - timedelta(days=CRAWL_WINDOW_END)
        logging.info(f"OSF crawl window: {osf_start_date.date()} to {osf_end_date.date()}")

        # Load past OSF IDs
        past_osf_ids = load_past_osf_ids()
        logging.info(f"Loaded {len(past_osf_ids)} past OSF IDs")

        # Retrieve OSF preprints
        logging.info("Retrieving preprints from OSF API...")
        try:
            osf_items = retrieve_osf_preprints(osf_start_date, osf_end_date)
            logging.info(f"Retrieved {len(osf_items)} raw items from OSF")

            if osf_items:
                # Parse OSF articles
                osf_articles = parse_osf_response(osf_items)
                logging.info(f"Parsed {len(osf_articles)} OSF articles")

                # Deduplicate versions (keep latest)
                osf_articles = deduplicate_osf_versions(osf_articles)
                logging.info(f"After version deduplication: {len(osf_articles)} articles")

                # Remove past preprints
                osf_articles = remove_past_osf_preprints(osf_articles, past_osf_ids)
                logging.info(f"After removing past preprints: {len(osf_articles)} new preprints")

                if osf_articles:
                    # Clean OSF data
                    osf_articles = clean_osf_data(osf_articles)
                    logging.info("Cleaned OSF article data")

                    # No categorization - subjects remain as raw level 2 categories
                    logging.info(f"Keeping {len(osf_articles)} preprints with raw subjects")

                    # Render OSF JSON
                    osf_json_content = render_osf_json(osf_articles, now.date())

                    # Write output to preprints.json file
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    osf_output_path = os.path.join(OUTPUT_DIR, "preprints.json")
                    with open(osf_output_path, 'w', encoding='utf-8') as f:
                        f.write(osf_json_content)
                    logging.info(f"OSF output written to: {osf_output_path}")

                    # Update OSF ID memory
                    if UPDATE_MEMORY:
                        update_osf_id_memory(osf_articles)
                        logging.info(f"Updated OSF ID memory with {len(osf_articles)} IDs")
                    else:
                        logging.info("OSF ID memory update disabled in config")
                else:
                    logging.info("No new OSF preprints found.")
            else:
                logging.info("No OSF preprints found in date range.")

        except Exception as e:
            logging.error(f"Error during OSF crawl: {e}", exc_info=True)
            msg = "OSF crawl failed"
            if ENABLE_CROSSREF_CRAWL:
                msg += " but Crossref crawl was successful"
            logging.warning(msg)
    else:
        logging.info("\nOSF crawl disabled in config (ENABLE_OSF_CRAWL=False)")

    # Update statistics
    if UPDATE_STATS:
        logging.info("\n" + "="*50)
        logging.info("Updating statistics...")
        logging.info("="*50)
        try:
            update_stats_csv()
        except Exception as e:
            logging.error(f"Error updating statistics: {e}", exc_info=True)
            logging.warning("Statistics update failed, but crawl completed")
    else:
        logging.info("\nStatistics update disabled in config (UPDATE_STATS=False)")

    logging.info("\n" + "="*50)
    logging.info("Crawl completed successfully")
    logging.info("="*50)


if __name__ == "__main__":
    main()
