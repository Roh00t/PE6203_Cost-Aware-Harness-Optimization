#!/usr/bin/env python3
"""Copy the logs behind a run from jobs/ (git-ignored) into results/ (committed).

    python3 scripts/export_run.py jobs/<run> results/<area>/<name>

Keeps what a reader needs to check a number: each trial's result.json, config.json,
trial.log, agent and verifier logs, and small JSON/TXT artifacts. Leaves out browser
profiles, images, models and anything over 2 MB. Refuses to export if any file looks like
it contains an API key. Also writes summary.json (see summarize_run.py).
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 2 * 1024 * 1024
ARTIFACT_SUFFIXES = {".json", ".txt"}
SECRET_RE = re.compile(rb"AIza[0-9A-Za-z_-]{20,}|sk-or-v1-[0-9a-f]{20,}|sk-[A-Za-z0-9]{20,}")


def wanted(rel: Path, size: int) -> bool:
    if size > MAX_BYTES:
        return False
    if "artifacts" in rel.parts:
        return rel.suffix in ARTIFACT_SUFFIXES and rel.name not in {"Preferences", "Local State"}
    return True


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    if not src.is_dir():
        sys.exit(f"no such run: {src}")

    subprocess.run([sys.executable, str(Path(__file__).with_name("summarize_run.py")), str(src)],
                   check=True, stdout=subprocess.DEVNULL)

    files, skipped = [], 0
    for path in sorted(p for p in src.rglob("*") if p.is_file()):
        rel = path.relative_to(src)
        if wanted(rel, path.stat().st_size):
            files.append(rel)
        else:
            skipped += 1

    leaks = [str(rel) for rel in files if SECRET_RE.search((src / rel).read_bytes())]
    if leaks:
        sys.exit("refusing to export; possible API key in:\n  " + "\n  ".join(leaks))

    for rel in files:
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, dest / rel)
    size = sum((dest / rel).stat().st_size for rel in files)
    print(f"exported {len(files)} files ({size / 1e6:.1f} MB) to {dest}; skipped {skipped} "
          f"(browser profiles, images, large files)")


if __name__ == "__main__":
    main()
