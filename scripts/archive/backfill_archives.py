#!/usr/bin/env python3
"""
Backfill historical archive snapshots from gh-pages git history.

For each edition in gh-pages history, checks out the exact historical commit
(templates + data), runs Jekyll, post-processes the HTML, and writes the result
to archive/{date}/ on the gh-pages branch.

Run from the repo root (main branch checked out):
  python3 scripts/archive/backfill_archives.py

Prerequisites:
  gem install bundler
  pip3 install beautifulsoup4
"""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
BUNDLE_PATH = Path("/tmp/ppicnic-gems")
GHPAGES_WORKTREE = Path("/tmp/ppicnic-ghpages")

HTML_PAGES = [
    "index.html",
    "political_science.html",
    "economics.html",
    "sociology.html",
    "international_relations.html",
    "public_administration.html",
    "multidisciplinary.html",
    "migration_studies.html",
    "communication_studies.html",
    "environmental_studies.html",
    "working_papers.html",
]

BACKFILL_CONFIG = """\
exclude:
  - Gemfile
  - Gemfile.lock
  - credentials.R
  - archive
  - data
  - data.md
  - _config_backfill.yml
"""

BUNDLE_ENV = {**os.environ, "BUNDLE_PATH": str(BUNDLE_PATH)}


# ---------------------------------------------------------------------------
# Post-processing (inlined from scripts/archive_postprocess.py)
# ---------------------------------------------------------------------------

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
    "/archive", "/archive.html",
}

LOCAL_ASSETS = {
    "/assets/css/custom.css",
    "/assets/js/custom.js",
    "/assets/js/storage.js",
}

DEACTIVATE_HREFS = {
    "/notifications", "/notifications.html",
    "https://nep.repec.org/",
    "https://nep.repec.org",
}


def _deactivate_links(soup):
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href in DEACTIVATE_HREFS or href.rstrip("/").endswith("/notifications"):
            del link["href"]
            link["tabindex"] = "-1"
            link["aria-disabled"] = "true"
            link["style"] = "pointer-events: none; opacity: 0.5; cursor: default;"


def _rewrite_links(soup, archive_prefix):
    for tag in soup.find_all(href=True):
        href = tag["href"]
        if href in LOCAL_ASSETS:
            tag["href"] = "." + href
        elif href in INTERNAL_PATHS or any(
            href == p or href.startswith(p + "?") or href.startswith(p + "#")
            for p in INTERNAL_PATHS if p != "/"
        ):
            if href in ("/", "/index.html"):
                tag["href"] = archive_prefix + "/"
            else:
                tag["href"] = archive_prefix + href.replace(".html", "")
        elif href == "/":
            tag["href"] = archive_prefix + "/"

    for tag in soup.find_all(src=True):
        if tag["src"] in LOCAL_ASSETS:
            tag["src"] = "." + tag["src"]


def _inject_banner(soup, date_str):
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


def postprocess_file(html_path, archive_prefix, date_str):
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    _deactivate_links(soup)
    _rewrite_links(soup, archive_prefix)
    _inject_banner(soup, date_str)
    html_path.write_text(str(soup), encoding="utf-8")


# ---------------------------------------------------------------------------
# Archive index update (inlined from scripts/archive_update_index.py)
# ---------------------------------------------------------------------------

def update_archive_index(ghpages_dir, date):
    idx_path = ghpages_dir / "_data" / "archive_index.json"
    try:
        idx = json.loads(idx_path.read_text())
    except Exception:
        idx = []
    if not any(e["date"] == date and e.get("version") == "v1" for e in idx):
        idx.insert(0, {"date": date, "version": "v1"})
        idx.sort(key=lambda x: x["date"], reverse=True)
        idx_path.write_text(json.dumps(idx, indent=2))
        print(f"  Added {date} (v1) to archive index.")
    else:
        print(f"  Entry for {date} (v1) already in archive index.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, cwd=None, env=None, check=True):
    subprocess.run(cmd, cwd=cwd, env=env or os.environ, check=check, text=True)


def git_capture(*args, cwd=None):
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd or REPO_ROOT,
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_ghpages_worktree():
    subprocess.run(["git", "worktree", "prune"], cwd=REPO_ROOT, capture_output=True)
    if GHPAGES_WORKTREE.exists():
        print(f"  Using existing gh-pages worktree: {GHPAGES_WORKTREE}")
    else:
        print(f"  Creating gh-pages worktree: {GHPAGES_WORKTREE}")
        git_capture("worktree", "add", str(GHPAGES_WORKTREE), "gh-pages")
    return GHPAGES_WORKTREE


def collect_editions(ghpages_dir):
    """Return (date, hash) pairs not yet archived, oldest-first.

    Scans ALL gh-pages commits so manual fix commits are picked up automatically.
    git log is newest-first, so the first occurrence of each date is the most-recent
    (possibly manually-corrected) state for that edition.
    """
    hashes = git_capture("log", "--format=%H", "gh-pages").splitlines()
    seen = set()
    editions = []
    for h in hashes:
        try:
            raw = git_capture("show", f"{h}:_data/publications.json")
            date = json.loads(raw).get("update", "").strip()
        except Exception:
            continue
        if not date or date in seen:
            continue
        seen.add(date)
        if (ghpages_dir / "archive" / date / "index.html").exists():
            print(f"  Skipping {date} — already archived")
            continue
        editions.append((date, h))
    editions.sort(key=lambda x: x[0])
    return editions


def get_gemfile_fallback():
    """Return oldest gh-pages commit that has a Gemfile (for the one pre-Gemfile edition)."""
    hashes = git_capture("log", "--format=%H", "gh-pages", "--", "Gemfile").splitlines()
    if not hashes:
        raise RuntimeError("No Gemfile found in gh-pages history.")
    return hashes[-1]


# ---------------------------------------------------------------------------
# Per-edition build
# ---------------------------------------------------------------------------

def build_edition(date, commit_hash, ghpages_dir, gemfile_fallback_hash):
    build_dir = Path(f"/tmp/ppicnic-{date}")
    print(f"\n{'─'*60}")
    print(f"  {date}  (commit {commit_hash[:8]})")

    try:
        if build_dir.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(build_dir)],
                cwd=REPO_ROOT, capture_output=True,
            )

        git_capture("worktree", "add", "--detach", str(build_dir), commit_hash)

        if not (build_dir / "Gemfile").exists():
            print(f"  Injecting Gemfile from {gemfile_fallback_hash[:8]}...")
            for fname in ("Gemfile", "Gemfile.lock"):
                try:
                    (build_dir / fname).write_text(
                        git_capture("show", f"{gemfile_fallback_hash}:{fname}")
                    )
                except Exception:
                    print(f"  WARNING: could not inject {fname}")

        (build_dir / "_config_backfill.yml").write_text(BACKFILL_CONFIG)

        print("  bundle install...")
        run(["bundle", "install"], cwd=build_dir, env=BUNDLE_ENV)

        print("  jekyll build...")
        run(
            ["bundle", "exec", "jekyll", "build",
             "--baseurl", "",
             "--config", "_config.yml,_config_backfill.yml"],
            cwd=build_dir, env=BUNDLE_ENV,
        )

        site_dir = build_dir / "_site"
        dest = ghpages_dir / "archive" / date
        (dest / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (dest / "assets" / "js").mkdir(parents=True, exist_ok=True)

        copied = 0
        for page in HTML_PAGES:
            src = site_dir / page
            if src.exists():
                shutil.copy2(src, dest / page)
                copied += 1
            else:
                print(f"  WARNING: {page} missing from _site/")
        print(f"  Copied {copied}/{len(HTML_PAGES)} HTML pages")

        for rel_src, rel_dst in [
            ("assets/css/custom.css", "assets/css/custom.css"),
            ("assets/js/custom.js",   "assets/js/custom.js"),
            ("assets/js/storage.js",  "assets/js/storage.js"),
        ]:
            src = build_dir / rel_src
            if src.exists():
                shutil.copy2(src, dest / rel_dst)
            else:
                print(f"  WARNING: {rel_src} not found in historical worktree")

        print("  post-processing HTML...")
        archive_prefix = f"/archive/{date}"
        for html_path in sorted(dest.glob("*.html")):
            postprocess_file(html_path, archive_prefix, date)

        update_archive_index(ghpages_dir, date)
        print("  OK")

    finally:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(build_dir)],
            cwd=REPO_ROOT, capture_output=True,
        )


# ---------------------------------------------------------------------------
# Commit
# ---------------------------------------------------------------------------

def commit_archives(ghpages_dir):
    for cmd in [
        ["git", "config", "user.email", "m.marbach@ucl.ac.uk"],
        ["git", "config", "user.name", "Moritz Marbach"],
        ["git", "add", "archive/", "_data/archive_index.json"],
    ]:
        subprocess.run(cmd, cwd=ghpages_dir, check=True)

    staged = subprocess.run(
        ["git", "diff", "--staged", "--quiet"], cwd=ghpages_dir,
    )
    if staged.returncode == 0:
        print("\nNothing new to commit — all editions already archived.")
    else:
        subprocess.run(
            ["git", "commit", "-m", "Backfill historical archives"],
            cwd=ghpages_dir, check=True,
        )
        print(f"\nCommitted. To push:\n  cd {ghpages_dir} && git push origin gh-pages")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Paper Picnic — Historical Archive Backfill")
    print(f"Repo: {REPO_ROOT}\n")

    ghpages_dir = setup_ghpages_worktree()

    print("Scanning gh-pages history...")
    editions = collect_editions(ghpages_dir)

    if not editions:
        print("\nAll editions already archived — nothing to do.")
        return

    gemfile_fallback = get_gemfile_fallback()

    print(f"\n{len(editions)} edition(s) to process:")
    for date, h in editions:
        print(f"  {date}  {h[:8]}")
    print()

    for date, commit_hash in editions:
        build_edition(date, commit_hash, ghpages_dir, gemfile_fallback)

    commit_archives(ghpages_dir)
    print("\nDone.")


if __name__ == "__main__":
    main()
