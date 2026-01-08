"""
Configuration and constants for Paper Picnic
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# API Credentials
OPENAI_API_KEY = os.environ.get("OPENAI_APIKEY", "")
CROSSREF_EMAIL = os.environ.get("CROSSREF_EMAIL", "")

# Crawl Configuration
CRAWL_WINDOW_START = 14  # days ago
CRAWL_WINDOW_END = 1     # days ago
UPDATE_MEMORY = True  # whether to update memory/doi.csv and memory/osf_ids.csv
UPDATE_STATS = True  # whether to update output/stats.csv after crawl
LIMIT_JOURNALS = None  # limit number of journals to crawl (None = all journals, or set to int like 5)

# Enable/Disable Crawlers
ENABLE_CROSSREF_CRAWL = True   # Set to False to skip Crossref journal crawl
ENABLE_OSF_CRAWL = True        # Set to False to skip OSF preprints crawl

# Filter Configuration
ENABLE_AI_FILTER = True        # Set to False to skip OpenAI classification for Crossref articles

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT = 30  # seconds
OPENAI_RETRY_BACKOFF = 5  # seconds

# OpenAI System Prompt (ported from parameters/prompts.R)
PROMPT_SOCSCI_CLASSIFIER = (
    "You are given a content from a new issue of a multidisciplinary scientific journal. "
    "Respond 'Yes' if the content is a research article in any social science discipline "
    "and 'No' otherwise."
)

# Filter Codes
FILTER_PASS = 0           # Article passes all filters
FILTER_ERROR = -1         # Error in AI filtering (still show article)
FILTER_STANDARD = 1       # Standard filter (ToC, editorial, erratum)
FILTER_AI_REJECT = 2      # AI rejected as non-social-science
FILTER_SCIENCE = 3        # Science filter (abstract too short)
FILTER_NATURE = 4         # Nature filter (URL pattern)

# Crossref API Configuration
CROSSREF_API_BASE = "https://api.crossref.org"
CROSSREF_TIMEOUT = 60     # seconds
CROSSREF_ROWS = 1000      # max rows per request
CROSSREF_RETRY_BACKOFF = 5  # seconds

# OSF API Configuration
OSF_API_BASE = "https://api.osf.io/v2"
OSF_TIMEOUT = 30  # seconds

# File Paths
PARAMETERS_DIR = "./parameters"
MEMORY_DIR = "./memory"
OUTPUT_DIR = "./output"
LOGS_DIR = "./logs"
