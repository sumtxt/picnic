# Paper Picnic 2.0

A weekly basket with the latest published research in political science. On Fridays at 2 AM UTC, we query the Crossref API for new research articles that appeared in the previous 7 days across many journals in political science and adjacent fields. [paper-picnic.com/](https://paper-picnic.com/)

The crawler lives in the `main` branch of the backend while the website is rendered from the `gh-pages` branch. 

## Setup

### Local Development

1. **Install Python 3.11**

   ```bash
   pyenv install 3.11
   pyenv local 3.11
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt

   # For development (includes testing tools)
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:

   ```bash
   OPENAI_APIKEY=your_openai_api_key
   CROSSREF_EMAIL=your_email@example.com
   ```

### GitHub Actions Setup

After forking the repository, you need to configure repository settings:

1. **Enable Workflow Permissions**
   - Go to Settings > Actions > General
   - Scroll to "Workflow permissions"
   - Allow workflows to read and write in the repository

2. **Set Repository Secrets**
   - Go to Security > Secrets and Variables > Actions
   - Add the following secrets:
     - `OPENAI_APIKEY` - OpenAI API key for article classification
     - `CROSSREF_EMAIL` - Your email for polite Crossref API requests
     - `RESEND_API_KEY` - Resend.com API key for email notifications
     - `RESEND_EMAIL_FROM` - Sender email address
     - `RESEND_EMAIL_TO` - Recipient email address

## Usage

### Local Crawl

Run the crawler

```bash
python main.py
```

Use the parameters in `./src/config.py` to disable some features of the crawler for local testing purposes. 

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term --cov-report=html

# Run specific test file
pytest tests/test_parsers.py
```


## Project Structure

```
picnic/
├── src/                      # Source code modules
│   ├── config.py             # Configuration and constants
│   ├── crossref_client.py    # Crossref API client
│   ├── openai_client.py      # OpenAI API integration
|   ├── osf_client.py         # OSF API client
│   ├── parsers.py            # Response parsing
│   ├── filters.py            # Article filtering logic
│   ├── data_processor.py     # Data cleaning and deduplication
│   ├── json_renderer.py      # JSON output formatting
│   └── stats_updater.py      # Statistics management
├── main.py                   # Main crawl script
├── tests/                    # Unit tests
├── parameters/               # Journal/OSF configurations
├── memory/                   # Crawl history for deduplication
├── output/                   # Generated JSON files and statistics
├── notification/             # Email notification system (Node.js)
├── .github/workflows/        # GitHub Actions automation
└── requirements.txt          # Python dependencies
```

## How It Works

The crawler ([main.py](main.py)) runs two parallel workflows:

### 1. Crossref Journal Crawl

1. Tests Crossref API endpoints (public vs polite) to select the faster one
2. Queries `/works` endpoint with batched ISSNs from [parameters/journals.json](parameters/journals.json)
3. Searches both `created` and `published` dates (default: 14 days ago to 1 day ago)
4. Parses metadata and removes duplicates using [memory/doi.csv](memory/doi.csv)
5. Merges journal info and applies filters:
   - **Standard**: Removes editorials, ToCs, errata by title pattern
   - **Nature**: Keeps only articles with `/s` in URL
   - **Science**: Keeps only articles with abstracts ≥200 chars
   - **AI** (optional): Uses GPT-4o-mini to classify social science relevance
6. Outputs to [output/publications.json](output/publications.json)

### 2. OSF Preprints Crawl

1. Loads subject filter from [parameters/osf_subjects.json](parameters/osf_subjects.json) ("Social and Behavioral Sciences")
2. Queries OSF API date-by-date within crawl window
3. Parses metadata, deduplicates versions (keeps latest), removes past preprints using [memory/osf_ids.csv](memory/osf_ids.csv)
4. Outputs to [output/preprints.json](output/preprints.json)

### 3. Statistics & Automation

- **Stats**: Counts articles per journal, updates [output/stats.csv](output/stats.csv)
- **GitHub Actions**:
  - [Crawl workflow](.github/workflows/crawl.yml) runs [main.py](main.py) (manual trigger)
  - [Update Website workflow](.github/workflows/update_website.yml) syncs outputs to `gh-pages` branch

Behavior is configurable via [src/config.py](src/config.py) (crawl window, memory updates, filter toggles, etc.)

## History 

The first version of the crawler went live in August 2024. Paper Picnic 2.0, rewritten in Python by Claude Code based on the original R version, launched in February 2026 after running side-by-side since January. The legacy R crawler remains available in the `main_v0` branch, and the original website in `gh-pages_v0`.
