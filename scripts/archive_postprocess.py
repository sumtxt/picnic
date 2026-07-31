"""
Post-processes archived HTML pages:
  - Rewrites absolute internal links to stay within the archive directory
  - Rewrites /assets/ links to use the local snapshot (./assets/)
  - Replaces the secondary nav bar with an amber archive banner

Usage: python3 archive_postprocess.py <archive_dir> <date>
  e.g. python3 archive_postprocess.py archive/2026-07-31 2026-07-31
"""

import sys
import re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

INTERNAL_PATHS = {
    "/", "/index.html",
    "/political_science", "/political_science.html",
    "/economics", "/economics.html",
    "/sociology", "/sociology.html",
    "/international_relations", "/international_relations.html",
    "/public_administration", "/public_administration.html",
    "/multidisciplinary", "/multidisciplinary.html",
    "/migration_studies", "/migration_studies.html",
    "/communication_studies", "/communication_studies.html",
    "/environmental_studies", "/environmental_studies.html",
    "/working_papers", "/working_papers.html",
    "/about", "/about.html",
    "/stats", "/stats.html",
    "/notifications", "/notifications.html",
    "/archive", "/archive.html",
}


def rewrite_links(soup, archive_prefix):
    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href.startswith("/assets/"):
            tag["href"] = "." + href
        elif href in INTERNAL_PATHS or any(
            href == p or href.startswith(p + "?") or href.startswith(p + "#")
            for p in INTERNAL_PATHS if p != "/"
        ):
            if href == "/" or href == "/index.html":
                tag["href"] = archive_prefix + "/"
            else:
                clean = href.rstrip(".html")
                tag["href"] = archive_prefix + clean
        elif href == "/":
            tag["href"] = archive_prefix + "/"

    for tag in soup.find_all(src=True):
        src = tag["src"]
        if src.startswith("/assets/"):
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
        container = new_inner.find(class_="container-fluid")
        container.append(theme_btn.extract())

    nav_bar.clear()
    nav_bar.append(new_inner)


def process_file(html_path, archive_prefix, date_str):
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    rewrite_links(soup, archive_prefix)
    inject_banner(soup, date_str)
    html_path.write_text(str(soup), encoding="utf-8")


def main():
    if len(sys.argv) != 3:
        print("Usage: archive_postprocess.py <archive_dir> <date>")
        sys.exit(1)

    archive_dir = Path(sys.argv[1])
    date_str = sys.argv[2]
    archive_prefix = f"/archive/{date_str}"

    html_files = list(archive_dir.glob("*.html"))
    if not html_files:
        print(f"No HTML files found in {archive_dir}")
        sys.exit(1)

    for html_path in html_files:
        print(f"Processing {html_path.name}...")
        process_file(html_path, archive_prefix, date_str)

    print(f"Done — processed {len(html_files)} files.")


if __name__ == "__main__":
    main()
