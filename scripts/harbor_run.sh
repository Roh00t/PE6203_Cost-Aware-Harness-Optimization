#!/usr/bin/env bash
# Run Harbor on the locked TUA-Bench subset with safe local defaults.
#
#   scripts/harbor_run.sh --agent oracle --job-name oracle-gate
#   SPLIT=dev scripts/harbor_run.sh --agent terminus-2 --model openrouter/<model>
#
# Extra arguments are passed through to `harbor run`. Pre-flight checks refuse
# to start (and spend credit) if the checkout, subset or Docker VM is wrong.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SPLIT="${SPLIT:-eval}"
ARGS_FILE="configs/${SPLIT}_tasks.args"
TUA_ROOT="data/TUA-Bench"
export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"
N_CONCURRENT="${N_CONCURRENT:-1}"

die() { echo "harbor_run: $*" >&2; exit 1; }

[[ -f "$ARGS_FILE" ]] || die "no $ARGS_FILE (SPLIT must be eval or dev)"
[[ -d "$TUA_ROOT/tasks" ]] || die "missing $TUA_ROOT; see README 'Evaluation Subset > Reproduce'"

# 1. Benchmark checkout: pinned commit, tasks and verifiers unmodified.
want_sha="$(python3 -c 'import json; print(json.load(open("configs/task_subset.json"))["tua_bench_commit"])')"
have_sha="$(git -C "$TUA_ROOT" rev-parse HEAD)"
[[ "$have_sha" == "$want_sha" ]] || die "TUA-Bench at $have_sha, subset was drawn at $want_sha"
[[ -z "$(git -C "$TUA_ROOT" status --porcelain --untracked-files=no -- tasks dataset.toml)" ]] \
    || die "TUA-Bench tasks/verifiers have local modifications"

# 2. Harbor resolves the args file to exactly the intended tasks.
uv run --frozen python scripts/check_harbor_filter.py "$ARGS_FILE"

# 3. Docker VM can fit the largest task at the chosen concurrency
#    (Harbor's own default of 4 concurrent 8 GB trials would OOM a 16 GB Mac).
need_mb="$(python3 - "$ARGS_FILE" <<'EOF'
import json, sys
ids = open(sys.argv[1]).read().split()[1::2]
tasks = json.load(open("configs/task_subset.json"))["tasks"]
print(max(tasks[t]["memory_mb"] for t in ids))
EOF
)"
have_mb=$(( $(docker info --format '{{.MemTotal}}') / 1024 / 1024 ))
(( have_mb >= need_mb * N_CONCURRENT )) || die "Docker VM has ${have_mb} MB; ${SPLIT} split needs ${need_mb} MB x ${N_CONCURRENT} concurrent. Raise Docker Desktop > Settings > Resources > Memory, or lower N_CONCURRENT."

# --no-delete keeps built task images, so later configurations reuse them
# instead of rebuilding (Harbor's default --delete runs `down --rmi all`).
# shellcheck disable=SC2046  # word-splitting the args file is intended
exec uv run --frozen harbor run \
    -p "$TUA_ROOT/tasks" \
    $(cat "$ARGS_FILE") \
    --n-concurrent "$N_CONCURRENT" \
    --no-delete \
    --jobs-dir jobs \
    "$@"
