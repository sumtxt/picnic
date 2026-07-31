"""
Updates _data/archive_index.json with a new entry for the given date.
Run from the gh-pages checkout directory.

Usage: python3 archive_update_index.py <date>
  e.g. python3 archive_update_index.py 2026-07-31
"""

import sys
import json
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print("Usage: archive_update_index.py <date>")
        sys.exit(1)

    date = sys.argv[1]
    idx_path = Path("_data/archive_index.json")

    try:
        idx = json.loads(idx_path.read_text())
    except Exception:
        idx = []

    if not any(e["date"] == date and e.get("version") == "v1" for e in idx):
        idx.insert(0, {"date": date, "version": "v1"})
        idx.sort(key=lambda x: x["date"], reverse=True)
        idx_path.write_text(json.dumps(idx, indent=2))
        print(f"Added {date} (v1) to archive index.")
    else:
        print(f"Entry for {date} (v1) already in archive index.")


if __name__ == "__main__":
    main()
