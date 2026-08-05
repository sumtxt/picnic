"""
Archives the currently published edition of the live site:
  - Reads the published date from publications.json
  - Fetches the live pages and assets into archive/<date>/
  - Post-processes the HTML for standalone viewing (rewrites internal links,
    deactivates non-archived links, injects an archive banner)
  - Records the new snapshot in _data/archive_index.json

Skips fetching if archive/<date>/ already exists. If run inside GitHub
Actions (GITHUB_ENV set), also exports PREV_DATE for later workflow steps.

Run from the gh-pages checkout directory.

Usage: python3 archive_snapshot.py
"""

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

BASE = "https://www.paper-picnic.com"
RETRIES = 3
INDEX_VERSION = "v1"
USER_AGENT = "Mozilla/5.0 (compatible; archive-snapshot-bot)"

# Page slugs fetched into each snapshot
PAGES = [
    "", "political_science", "economics", "sociology",
    "international_relations", "public_administration",
    "multidisciplinary", "migration_studies",
    "communication_studies", "environmental_studies", "working_papers",
]

# Static asset paths fetched into each snapshot
ASSETS = [
    "assets/css/custom.css",
    "assets/js/custom.js",
    "assets/js/storage.js",
]

# PAGES as site-relative paths (both slug and .html forms) — only pages that
# are actually fetched should have their links rewritten into the archive
INTERNAL_PATHS = {"/", "/index.html"} | {
    path
    for page in PAGES if page
    for path in (f"/{page}", f"/{page}.html")
}

# ASSETS as absolute site paths, for matching hrefs/srcs during rewriting
LOCAL_ASSETS = {"/" + asset for asset in ASSETS}

# Links deactivated rather than rewritten — not archived, visually dimmed
DEACTIVATE_HREFS = {
    "/notifications", "/notifications.html",
    "https://nep.repec.org/",
    "https://nep.repec.org",
}


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_url(url):
    last_error = None
    for _ in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read()
        except Exception as e:
            last_error = e
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def get_prev_date():
    data = json.loads(fetch_url(f"{BASE}/data/publications.json"))
    return data["update"]


def fetch_snapshot(archive_dir):
    (archive_dir / "assets" / "css").mkdir(parents=True, exist_ok=True)
    (archive_dir / "assets" / "js").mkdir(parents=True, exist_ok=True)

    for page in PAGES:
        filename = f"{page or 'index'}.html"
        (archive_dir / filename).write_bytes(fetch_url(f"{BASE}/{page}"))

    for asset in ASSETS:
        (archive_dir / asset).write_bytes(fetch_url(f"{BASE}/{asset}"))


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def deactivate_links(soup):
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Also match already-rewritten forms like /archive/DATE/notifications
        if href in DEACTIVATE_HREFS or href.rstrip("/").endswith("/notifications"):
            del link["href"]
            link["tabindex"] = "-1"
            link["aria-disabled"] = "true"
            link["style"] = "pointer-events: none; opacity: 0.5; cursor: default;"


def rewrite_links(soup, archive_prefix):
    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href in LOCAL_ASSETS:
            tag["href"] = "." + href
        elif any(
            href == p or href.startswith(p + "?") or href.startswith(p + "#")
            for p in INTERNAL_PATHS
        ):
            if href in ("/", "/index.html"):
                tag["href"] = archive_prefix + "/"
            else:
                tag["href"] = archive_prefix + href.replace(".html", "")

    for tag in soup.find_all(src=True):
        src = tag["src"]
        if src in LOCAL_ASSETS:
            tag["src"] = "." + src


def inject_banner(soup, date_str):
    try:
        display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        display_date = date_str

    nav_bar = soup.find(class_="secondary-nav-bar")
    if not nav_bar:
        return

    nav_bar["style"] = "background: #f59e0b !important; color: #1a1a1a !important;"
    theme_btn = nav_bar.find("button", id="bd-theme")

    banner_html = f"""
<div class="container-fluid d-flex justify-content-between align-items-center">
  <div>
    📦 Archived edition &middot; {display_date} &middot; You are viewing a past issue.
    <a href="https://www.paper-picnic.com/"
       style="color: #1a1a1a; font-weight: 600; text-decoration: underline;">Go to current &rarr;</a>
  </div>
</div>
"""
    new_inner = BeautifulSoup(banner_html, "html.parser")
    if theme_btn:
        new_inner.find(class_="container-fluid").append(theme_btn.extract())

    nav_bar.clear()
    nav_bar.append(new_inner)


def postprocess_snapshot(archive_dir, archive_prefix, date_str):
    for html_path in sorted(archive_dir.glob("*.html")):
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        deactivate_links(soup)
        rewrite_links(soup, archive_prefix)
        inject_banner(soup, date_str)
        html_path.write_text(str(soup), encoding="utf-8")


# ---------------------------------------------------------------------------
# Archive index
# ---------------------------------------------------------------------------

def update_archive_index(date_str):
    idx_path = Path("_data/archive_index.json")
    try:
        idx = json.loads(idx_path.read_text())
    except Exception:
        idx = []

    if any(e["date"] == date_str and e.get("version") == INDEX_VERSION for e in idx):
        print(f"Entry for {date_str} ({INDEX_VERSION}) already in archive index.")
        return

    idx.insert(0, {"date": date_str, "version": INDEX_VERSION})
    idx.sort(key=lambda x: x["date"], reverse=True)
    idx_path.write_text(json.dumps(idx, indent=2))
    print(f"Added {date_str} ({INDEX_VERSION}) to archive index.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def export_to_github_env(date_str):
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a") as f:
            f.write(f"PREV_DATE={date_str}\n")


def main():
    date_str = get_prev_date()
    export_to_github_env(date_str)

    archive_dir = Path("archive") / date_str
    if (archive_dir / "index.html").exists():
        print(f"Archive for {date_str} already exists — skipping.")
        return

    print(f"Fetching snapshot for {date_str}...")
    fetch_snapshot(archive_dir)

    print("Post-processing HTML...")
    postprocess_snapshot(archive_dir, f"/archive/{date_str}", date_str)

    update_archive_index(date_str)
    print(f"Done — archived {date_str}.")


if __name__ == "__main__":
    main()
