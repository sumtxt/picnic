#!/usr/bin/env python3
"""
One-time cleanup of historical archive/<date>/ snapshots on gh-pages.

Every archived snapshot was fetched back when the live site still pulled
jQuery, Bootstrap, SortableJS, Google Fonts, and the Buy Me a Coffee button
widget from external CDNs. The live site has since been switched to local
copies under assets/vendor/, but the already-committed archive pages still
point at the old CDN URLs. This script rewrites every archived page to use
local vendor assets instead, and strips analytics beacons (Cabin, Cloudflare
Web Analytics).

Run from a gh-pages checkout (or worktree):
  python3 scripts/archive/localize_cdns.py
"""

import shutil
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path.cwd()
VENDOR_SRC = REPO_ROOT / "assets" / "vendor"

# Relative (site-root) vendor files copied into every archive/<date>/ dir.
VENDOR_FILES = [
    "vendor/css/bootstrap-5.3.3.min.css",
    "vendor/css/inter-fonts.css",
    "vendor/js/jquery-3.7.1.min.js",
    "vendor/js/sortable-1.15.0.min.js",
    "vendor/js/bootstrap-5.3.3.bundle.min.js",
    "vendor/img/bmc-button.png",
    "vendor/fonts/inter-v20-cyrillic-ext.woff2",
    "vendor/fonts/inter-v20-cyrillic.woff2",
    "vendor/fonts/inter-v20-greek-ext.woff2",
    "vendor/fonts/inter-v20-greek.woff2",
    "vendor/fonts/inter-v20-latin-ext.woff2",
    "vendor/fonts/inter-v20-latin.woff2",
    "vendor/fonts/inter-v20-vietnamese.woff2",
]

def coffee_button_tag(soup):
    a = soup.new_tag("a", href="https://buymeacoffee.com/mmarbach",
                      target="_blank", rel="noopener")
    img = soup.new_tag("img", src="./assets/vendor/img/bmc-button.png",
                        alt="Buy me a coffee",
                        style="height: 60px; width: auto;")
    a.append(img)
    return a


def process_html(html_path):
    original = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(original, "html.parser")
    changed = False

    # jQuery / SortableJS / Bootstrap JS bundle CDN <script src=...>
    for tag in soup.find_all("script", src=True):
        src = tag["src"]
        if "cdn.jsdelivr.net/npm/jquery@3.7.1" in src:
            tag.attrs = {"src": "./assets/vendor/js/jquery-3.7.1.min.js"}
            changed = True
        elif "cdn.jsdelivr.net/npm/sortablejs@1.15.0" in src:
            tag.attrs = {"src": "./assets/vendor/js/sortable-1.15.0.min.js"}
            changed = True
        elif "cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js" in src:
            tag.attrs = {"src": "./assets/vendor/js/bootstrap-5.3.3.bundle.min.js"}
            changed = True
        elif "cdnjs.buymeacoffee.com" in src:
            tag.replace_with(coffee_button_tag(soup))
            changed = True
        elif "scripts.withcabin.com" in src:
            tag.decompose()
            changed = True
        elif "static.cloudflareinsights.com" in src:
            tag.decompose()
            changed = True

    # Bootstrap CSS CDN <link href=...>
    for tag in soup.find_all("link", href=True):
        href = tag["href"]
        if "cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css" in href:
            tag.attrs = {"href": "./assets/vendor/css/bootstrap-5.3.3.min.css",
                         "rel": "stylesheet"}
            changed = True
        elif "fonts.googleapis.com/css2" in href:
            tag.attrs = {"href": "./assets/vendor/css/inter-fonts.css",
                         "rel": "stylesheet"}
            changed = True

    # Google Fonts preconnect hints — no longer needed, just drop them.
    for tag in soup.find_all("link", href=True):
        href = tag["href"]
        if href in ("https://fonts.googleapis.com", "https://fonts.gstatic.com"):
            tag.decompose()
            changed = True

    if changed:
        html_path.write_text(str(soup), encoding="utf-8")
    return changed


def copy_vendor_assets(archive_dir):
    copied_any = False
    for rel in VENDOR_FILES:
        src = VENDOR_SRC / Path(rel).relative_to("vendor")
        dst = archive_dir / "assets" / rel
        if not src.exists():
            print(f"  WARNING: missing source vendor file {src}")
            continue
        if dst.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied_any = True
    return copied_any


def main():
    archive_root = REPO_ROOT / "archive"
    if not archive_root.is_dir():
        raise SystemExit("No archive/ directory here — run from a gh-pages checkout.")
    if not VENDOR_SRC.is_dir():
        raise SystemExit("No assets/vendor/ directory here — vendor assets not found.")

    snapshot_dirs = sorted(d for d in archive_root.iterdir() if d.is_dir())
    print(f"Found {len(snapshot_dirs)} archived snapshots.\n")

    touched = 0
    for snap in snapshot_dirs:
        html_files = sorted(snap.glob("*.html"))
        snap_changed = False
        for html_path in html_files:
            if process_html(html_path):
                snap_changed = True
        if copy_vendor_assets(snap):
            snap_changed = True
        if snap_changed:
            touched += 1
            print(f"  {snap.name}: updated")

    print(f"\nDone — {touched}/{len(snapshot_dirs)} snapshots touched.")


if __name__ == "__main__":
    main()
