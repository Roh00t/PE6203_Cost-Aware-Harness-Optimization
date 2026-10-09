#!/usr/bin/env python3
"""Extract the TUA-Bench task-family table from the paper's Appendix B.

task.toml only carries a fine-grained `metadata.category`; the five task
families used for stratified sampling exist only in the paper, where every
task header reads "<Family> - <Subcategory> - <task-id>". This script parses
those headers from the arXiv HTML and cross-checks them against the official
dataset.toml before writing configs/task_families.json.

Usage:
    python3 scripts/extract_families.py                   # fetch from arXiv
    python3 scripts/extract_families.py --html paper.html # use a saved copy
"""

import argparse
import hashlib
import html
import json
import re
import sys
import tomllib
import urllib.request
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PAPER_URL = "https://arxiv.org/html/2606.28480v1"

# Counts implied by the paper's text (38.3% / 18.3% / 13.3% of 120) plus the
# remaining 36 split between the two families whose share is not stated.
EXPECTED_FAMILY_COUNTS = {
    "Office & Productivity": 46,
    "Web & Information": 22,
    "System & Software Operations": 19,
    "Scientific & Engineering": 17,
    "Multimedia & Design": 16,
}
EXPECTED_SUBCATEGORIES = 20

HEADER_RE = re.compile(
    r"(" + "|".join(map(re.escape, EXPECTED_FAMILY_COUNTS)) + r")"
    r"\s*[-–—]\s*([A-Za-z&,/ ]+?)\s*[-–—]\s*"
    r"(\d{3}-[a-z0-9]+(?:-[a-z0-9]+)*)"
)


def load_dataset_ids(dataset_toml: Path) -> list[str]:
    with dataset_toml.open("rb") as f:
        data = tomllib.load(f)
    return [t["name"].removeprefix("local/") for t in data["tasks"]]


def fetch_html(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "tua-subset/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def parse_headers(raw_html: bytes) -> dict[str, dict[str, str]]:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw_html.decode("utf-8")))
    text = re.sub(r"\s+", " ", text)
    table: dict[str, dict[str, str]] = {}
    for family, subcategory, task_id in HEADER_RE.findall(text):
        entry = {"family": family, "subcategory": subcategory.strip()}
        if task_id in table and table[task_id] != entry:
            sys.exit(f"Conflicting labels for {task_id}: {table[task_id]} vs {entry}")
        table[task_id] = entry
    return table


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--html", type=Path, help="local copy of the paper HTML")
    ap.add_argument("--url", default=PAPER_URL)
    ap.add_argument("--tua-root", type=Path, default=REPO_ROOT / "data" / "TUA-Bench")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "configs" / "task_families.json")
    args = ap.parse_args()

    raw = args.html.read_bytes() if args.html else fetch_html(args.url)
    table = parse_headers(raw)
    dataset_ids = load_dataset_ids(args.tua_root / "dataset.toml")

    # Fail loudly on any disagreement between the paper and the dataset.
    missing = sorted(set(dataset_ids) - set(table))
    extra = sorted(set(table) - set(dataset_ids))
    if missing or extra:
        sys.exit(f"Paper/dataset mismatch. In dataset only: {missing}; in paper only: {extra}")
    counts = dict(Counter(e["family"] for e in table.values()))
    if counts != EXPECTED_FAMILY_COUNTS:
        sys.exit(f"Family counts {counts} != expected {EXPECTED_FAMILY_COUNTS}")
    n_sub = len({(e["family"], e["subcategory"]) for e in table.values()})
    if n_sub != EXPECTED_SUBCATEGORIES:
        sys.exit(f"Found {n_sub} subcategories, expected {EXPECTED_SUBCATEGORIES}")

    out = {
        "_source": {
            "paper": args.url,
            "paper_html_sha256": hashlib.sha256(raw).hexdigest(),
            "section": "Appendix B (task headers: Family - Subcategory - ID)",
        },
        "family_counts": EXPECTED_FAMILY_COUNTS,
        "tasks": dict(sorted(table.items())),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(f"Wrote {len(table)} tasks across {len(counts)} families to {args.out}")
    for family, n in EXPECTED_FAMILY_COUNTS.items():
        print(f"  {family:<30} {n}")


if __name__ == "__main__":
    main()
