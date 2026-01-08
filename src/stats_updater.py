"""
Statistics 

Ported from stats.R

"""

import json
import csv
import os
import logging

from .config import OUTPUT_DIR


def update_stats_csv() -> None:
    """
    Update stats.csv (long format) with new article counts

    Appends new rows to the end of the CSV file with columns:
    id, journal_name, crawl_date, paper_count
    """
    # Read publications.json
    filepath = os.path.join(OUTPUT_DIR, "publications.json")

    if not os.path.exists(filepath):
        logging.error(f"Output file not found: {filepath}")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error reading {filepath}: {e}")
        return

    # Get crawl date and content
    crawl_date = data.get("update")
    content = data.get("content", [])

    if not crawl_date:
        logging.warning("No crawl date found in publications.json")
        return

    stats_file = os.path.join(OUTPUT_DIR, "stats.csv")

    # Check if this date already exists
    if os.path.exists(stats_file):
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("crawl_date") == crawl_date:
                        logging.info(f"Date {crawl_date} already exists in stats.csv. Skipping update.")
                        return
        except (IOError, csv.Error) as e:
            logging.error(f"Error reading stats file: {e}")
            return

    # Load all journals from parameters/journals.json
    journals_file = "parameters/journals.json"
    try:
        with open(journals_file, 'r', encoding='utf-8') as f:
            all_journals = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error reading journals file: {e}")
        return

    # Create a mapping of journal_id to paper count from publications.json
    journal_counts = {}
    for journal_data in content:
        journal_id = journal_data.get("journal_id")
        articles = journal_data.get("articles", [])
        if journal_id:
            journal_counts[journal_id] = len(articles)

    # Create new rows for ALL journals (including those with 0 articles)
    new_rows = []
    for journal in all_journals:
        journal_id = journal.get("id")
        journal_name = journal.get("name")

        if not journal_id or not journal_name:
            continue

        # Get count from publications.json, or 0 if not present
        paper_count = journal_counts.get(journal_id, 0)

        new_rows.append({
            "id": journal_id,
            "journal_name": journal_name,
            "crawl_date": crawl_date,
            "paper_count": paper_count
        })

    # Sort new rows by ID for consistency
    new_rows.sort(key=lambda x: x["id"])

    # Append to stats file
    try:
        file_exists = os.path.exists(stats_file)

        with open(stats_file, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["id", "journal_name", "crawl_date", "paper_count"])

            # Write header only if file doesn't exist
            if not file_exists:
                writer.writeheader()
                logging.info("Created new stats.csv file")

            writer.writerows(new_rows)

        logging.info(f"Stats updated successfully with date: {crawl_date}")
        logging.info(f"Appended {len(new_rows)} rows for {len(new_rows)} journals")

    except (IOError, csv.Error) as e:
        logging.error(f"Error writing stats file: {e}")
