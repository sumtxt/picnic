#!/usr/bin/env python3
"""
Backfill historical archive snapshots from the v0 version of Paper Picnic
(origin/gh-pages_v0, covering 2024-08-23 to 2026-02-20).

Archives are written to archive/YYYY-MM-DD/ on the current gh-pages branch.
Entries are added to _data/archive_index.json with {"date": ..., "version": "v0"}.

Run from the repo root (main branch checked out):
  python3 scripts/archive/backfill_archives_v0.py

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
V0_BRANCH = "origin/gh-pages_v0"

BUNDLE_ENV = {**os.environ, "BUNDLE_PATH": str(BUNDLE_PATH)}


# ---------------------------------------------------------------------------
# Post-processing (inlined from scripts/archive_postprocess_v0.py)
#
# V0 differences from the current version:
#   - No .secondary-nav-bar — banner injected as a fixed overlay at page top
#   - Nav uses relative links (./politics etc.) — no internal link rewriting
#   - Only local assets need path rewriting
# ---------------------------------------------------------------------------

_LOCAL_ASSETS_V0 = {
    "/assets/css/custom.css",
    "/assets/js/custom.js",
}

_DEACTIVATE_HREFS_V0 = {
    "./notifications",
    "https://preprint.paper-picnic.com/",
    "https://preprint.paper-picnic.com",
    "https://nep.repec.org/",
    "https://nep.repec.org",
}


def _rewrite_asset_links(soup):
    for tag in soup.find_all(href=True):
        if tag["href"] in _LOCAL_ASSETS_V0:
            tag["href"] = "." + tag["href"]
    for tag in soup.find_all(src=True):
        if tag["src"] in _LOCAL_ASSETS_V0:
            tag["src"] = "." + tag["src"]


def _deactivate_links(soup):
    for link in soup.find_all("a", href=True):
        if link["href"] in _DEACTIVATE_HREFS_V0:
            del link["href"]
            link["tabindex"] = "-1"
            link["aria-disabled"] = "true"
            link["style"] = "pointer-events: none; opacity: 0.5; cursor: default;"


def _inject_banner(soup, date_str):
    try:
        display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")
    except ValueError:
        display_date = date_str

    banner_html = (
        f'<div style="position:fixed; top:0; left:0; right:0; z-index:1035; '
        f'background:#f59e0b; color:#1a1a1a; padding:4px 24px; '
        f'font-size:0.75rem; text-align:center; '
        f'border-bottom:1px solid rgba(0,0,0,0.1);">'
        f'<div class="container-fluid d-flex justify-content-between align-items-center">'
        f'<div>'
        f'📦 Archived edition &middot; {display_date} &middot; '
        f'You are viewing a past issue. '
        f'<a href="https://www.paper-picnic.com/" '
        f'style="color:#1a1a1a; font-weight:600; text-decoration:underline;">'
        f'Go to current &rarr;</a>'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    banner = BeautifulSoup(banner_html, "html.parser")

    body = soup.find("body")
    if body:
        body.insert(0, banner)

    nav = soup.find("nav")
    if nav:
        existing = nav.get("style", "").rstrip(";").strip()
        nav["style"] = (existing + "; top:27px;" if existing else "top:27px;")


def postprocess_file(html_path, date_str):
    content = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")
    _rewrite_asset_links(soup)
    _deactivate_links(soup)
    _inject_banner(soup, date_str)
    html_path.write_text(str(soup), encoding="utf-8")


# ---------------------------------------------------------------------------
# Archive index update
# ---------------------------------------------------------------------------

def update_archive_index(ghpages_dir, date):
    idx_path = ghpages_dir / "_data" / "archive_index.json"
    try:
        idx = json.loads(idx_path.read_text())
    except Exception:
        idx = []
    if not any(e["date"] == date and e.get("version") == "v0" for e in idx):
        idx.append({"date": date, "version": "v0"})
        idx.sort(key=lambda x: x["date"], reverse=True)
        idx_path.write_text(json.dumps(idx, indent=2))
        print(f"  Added {date} (v0) to archive index.")
    else:
        print(f"  {date} (v0) already in archive index.")


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
    """Return (date, hash) pairs for v0 editions not yet archived, oldest-first.

    Scans ALL gh-pages_v0 commits so manual fix commits are picked up automatically.
    git log is newest-first — first occurrence per date = most-recent state.
    Falls back through several category JSON files to find the update date.
    """
    hashes = git_capture("log", "--format=%H", V0_BRANCH).splitlines()
    seen = set()
    editions = []
    for h in hashes:
        date = None
        for data_file in [
            "_data/politics.json",
            "_data/economics.json",
            "_data/sociology.json",
            "_data/multidisciplinary.json",
        ]:
            try:
                raw = git_capture("show", f"{h}:{data_file}")
                date = json.loads(raw).get("update", "").strip()
                if date:
                    break
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


# ---------------------------------------------------------------------------
# Per-edition build
# ---------------------------------------------------------------------------

def build_edition(date, commit_hash, ghpages_dir):
    build_dir = Path(f"/tmp/ppicnic-v0-{date}")
    print(f"\n{'─'*60}")
    print(f"  {date}  (commit {commit_hash[:8]})")

    try:
        if build_dir.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(build_dir)],
                cwd=REPO_ROOT, capture_output=True,
            )

        git_capture("worktree", "add", "--detach", str(build_dir), commit_hash)

        print("  bundle install...")
        run(["bundle", "install"], cwd=build_dir, env=BUNDLE_ENV)

        print("  jekyll build...")
        run(
            ["bundle", "exec", "jekyll", "build", "--baseurl", ""],
            cwd=build_dir, env=BUNDLE_ENV,
        )

        site_dir = build_dir / "_site"
        dest = ghpages_dir / "archive" / date
        (dest / "assets" / "css").mkdir(parents=True, exist_ok=True)
        (dest / "assets" / "js").mkdir(parents=True, exist_ok=True)

        html_files = [f for f in site_dir.glob("*.html") if f.name != "data.html"]
        for src in html_files:
            shutil.copy2(src, dest / src.name)
        print(f"  Copied {len(html_files)} HTML pages: {[f.name for f in html_files]}")

        for rel_src, rel_dst in [
            ("assets/css/custom.css", "assets/css/custom.css"),
            ("assets/js/custom.js",   "assets/js/custom.js"),
        ]:
            src = build_dir / rel_src
            if src.exists():
                shutil.copy2(src, dest / rel_dst)
            else:
                print(f"  WARNING: {rel_src} not found")

        print("  post-processing HTML...")
        for html_path in sorted(dest.glob("*.html")):
            postprocess_file(html_path, date)

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
        print("\nNothing new to commit.")
    else:
        subprocess.run(
            ["git", "commit", "-m", "Backfill v0 historical archives"],
            cwd=ghpages_dir, check=True,
        )
        print(f"\nCommitted. To push:\n  cd {ghpages_dir} && git push origin gh-pages")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Paper Picnic — V0 Historical Archive Backfill")
    print(f"Repo: {REPO_ROOT}\n")

    ghpages_dir = setup_ghpages_worktree()

    print("Scanning gh-pages_v0 history...")
    editions = collect_editions(ghpages_dir)

    if not editions:
        print("\nAll v0 editions already archived — nothing to do.")
        return

    print(f"\n{len(editions)} edition(s) to process:")
    for date, h in editions:
        print(f"  {date}  {h[:8]}")
    print()

    for date, commit_hash in editions:
        build_edition(date, commit_hash, ghpages_dir)

    commit_archives(ghpages_dir)
    print("\nDone.")


if __name__ == "__main__":
    main()
