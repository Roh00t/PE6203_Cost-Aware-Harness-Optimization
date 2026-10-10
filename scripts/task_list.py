#!/usr/bin/env python3
"""Print the task IDs of a split, with the oracle-gate amendments applied.

    python3 scripts/task_list.py eval             # sampled eval split + subset_amendments.json
    python3 scripts/task_list.py dev
    python3 scripts/task_list.py reserve          # unused reserves, by family, in substitution order
    python3 scripts/task_list.py eval --fingerprint

configs/task_subset.json (and its fingerprint) stays exactly as sampled; swaps live only in
configs/subset_amendments.json. Each amendment must replace a current eval task with the first
unused reserve of the same family, so the file cannot drift from the README's substitution rule.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

CONFIGS = Path(__file__).resolve().parent.parent / "configs"
AMENDMENT_FIELDS = {"removed", "added", "family", "cause", "evidence"}


def fingerprint(task_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(task_ids)).encode()).hexdigest()


def apply_amendments(subset: dict, amendments: list[dict]) -> tuple[list[str], dict[str, list[str]]]:
    """Return (amended eval IDs, unused reserves per family); exit on any invalid amendment."""
    eval_ids = list(subset["eval_task_ids"])
    unused = {fam: list(s["reserve"]) for fam, s in subset["families"].items()}
    for n, a in enumerate(amendments, 1):
        missing = AMENDMENT_FIELDS - a.keys()
        if missing:
            sys.exit(f"amendment {n}: missing fields {sorted(missing)}")
        family = subset["tasks"].get(a["removed"], {}).get("family")
        if a["removed"] not in eval_ids:
            sys.exit(f"amendment {n}: {a['removed']} is not in the eval split at that point")
        if a["family"] != family:
            sys.exit(f"amendment {n}: {a['removed']} is in family {family!r}, not {a['family']!r}")
        if not unused[family] or a["added"] != unused[family][0]:
            nxt = unused[family][0] if unused[family] else "none left"
            sys.exit(f"amendment {n}: next reserve for {family} is {nxt}, not {a['added']}")
        unused[family].pop(0)
        eval_ids[eval_ids.index(a["removed"])] = a["added"]
    return sorted(eval_ids), unused


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("split", choices=["eval", "dev", "reserve"])
    ap.add_argument("--fingerprint", action="store_true", help="print the split's fingerprint instead")
    args = ap.parse_args()

    subset = json.loads((CONFIGS / "task_subset.json").read_text())
    amendments = json.loads((CONFIGS / "subset_amendments.json").read_text())["amendments"]
    eval_ids, unused = apply_amendments(subset, amendments)
    ids = {
        "eval": eval_ids,
        "dev": subset["dev_task_ids"],
        "reserve": [t for fam in sorted(unused) for t in unused[fam]],
    }[args.split]
    print(fingerprint(ids) if args.fingerprint else "\n".join(ids))


if __name__ == "__main__":
    main()
