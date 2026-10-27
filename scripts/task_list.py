#!/usr/bin/env python3
"""Print the task IDs of a split, with the oracle-gate amendments applied.

    python3 scripts/task_list.py eval             # sampled eval split + subset_amendments.json
    python3 scripts/task_list.py dev
    python3 scripts/task_list.py reserve          # unused reserves, by family, in substitution order
    python3 scripts/task_list.py eval --fingerprint
    python3 scripts/task_list.py eval --args > /tmp/eval.args   # Harbor args (-i ID), amended

configs/eval_tasks.args is the *sampled* list (before the swaps); check the amended list with
`--args`, e.g. `python3 scripts/check_assets.py /tmp/eval.args`. Every call also checks the
frozen fingerprints and refuses to print anything if configs/ was edited.

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


def check_frozen(subset: dict, amendments: dict, eval_ids: list[str]) -> None:
    """Exit if a split no longer matches the fingerprint frozen with it."""
    for name, expected, ids in (
        ("sampled eval split", subset.get("eval_fingerprint"), subset["eval_task_ids"]),
        ("dev split", subset.get("dev_fingerprint"), subset["dev_task_ids"]),
        ("amended eval split", amendments.get("final_eval_fingerprint"), eval_ids),
    ):
        if expected and fingerprint(ids) != expected:
            sys.exit(f"task_list: the {name} no longer matches its frozen fingerprint "
                     f"{expected[:12]}...; configs/ was edited")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("split", choices=["eval", "dev", "reserve"])
    output = ap.add_mutually_exclusive_group()
    output.add_argument("--fingerprint", action="store_true", help="print the split's fingerprint instead")
    output.add_argument("--args", action="store_true", help="print Harbor arguments (-i ID per line)")
    args = ap.parse_args()

    subset = json.loads((CONFIGS / "task_subset.json").read_text())
    amendment_doc = json.loads((CONFIGS / "subset_amendments.json").read_text())
    eval_ids, unused = apply_amendments(subset, amendment_doc["amendments"])
    check_frozen(subset, amendment_doc, eval_ids)
    ids = {
        "eval": eval_ids,
        "dev": subset["dev_task_ids"],
        "reserve": [t for fam in sorted(unused) for t in unused[fam]],
    }[args.split]
    if args.fingerprint:
        print(fingerprint(ids))
    else:
        print("\n".join(f"-i {i}" for i in ids) if args.args else "\n".join(ids))


if __name__ == "__main__":
    main()
