#!/usr/bin/env bash
# Run Harbor on the locked TUA-Bench subset, one task at a time, with safe local defaults.
#
#   scripts/harbor_run.sh --split dev --mode oracle                 # free: reference solutions
#   scripts/harbor_run.sh --split dev --mode oracle --only 003-rebuild-energy-model,009-repair-org-chart-layout
#   scripts/harbor_run.sh --split eval --mode oracle --prune-cache  # disk-bounded run
#   CONFIRM_PAID=1 scripts/harbor_run.sh --split dev -- --agent mini-swe-agent --model openrouter/<id>
#
# Options (before any Harbor arguments):
#   --split dev|eval     task split (default: eval; env SPLIT also works)
#   --mode oracle|nop    shorthand for `--agent oracle|nop`
#   --only ID[,ID...]    run only these tasks (must belong to the split)
#   --rerun ID[,ID...]   set aside these tasks' earlier attempts in this run and run them again
#                        (for failures judged to be infrastructure, e.g. a network outage)
#   --prune-cache        after each task, shrink Docker's build cache to CACHE_KEEP_GB.
#                        Docker's cache is shared, so this also evicts the least recently
#                        used cache of other projects (regenerable, but slow to rebuild).
#   --dry-run            run the pre-flight checks, print the per-task commands, exit
#   --                   everything after this is passed to `harbor run` unchanged
# Unrecognised options are also passed through to `harbor run`.
#
# Environment: N_CONCURRENT (default 1), MIN_FREE_GB (default 10), CACHE_KEEP_GB (default 15),
# DOCKER_DEFAULT_PLATFORM (default linux/amd64), CONFIRM_PAID, CONFIRM_EVAL.
#
# Pause and resume: Ctrl+C stops the run; re-running the same command with the same --job-name
# skips finished tasks and restarts the interrupted one. Tasks whose every trial ended in an
# exception (Docker or network failure) are rerun automatically: infrastructure errors are
# never scored (system_architecture.md §10.3). Earlier attempts are kept as <task>.<reason>-<time>/.
#
# Disk policy: each task is its own Harbor job under jobs/<run>/<task>/. Harbor deletes each
# trial's image afterwards (--delete); the build cache keeps rebuilds of the same task fast.
# Before every task the script checks free disk and stops cleanly below MIN_FREE_GB, because
# a full disk can corrupt Docker's VM. Summarise a run with scripts/summarize_run.py.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

die() { echo "harbor_run: $*" >&2; exit 1; }
say() { echo "harbor_run: $*"; }

SPLIT="${SPLIT:-eval}"
MODE=""
ONLY=""
RERUN=""
PRUNE=0
DRY_RUN=0
PASSTHROUGH=()
while (($#)); do
    case "$1" in
        --split) [[ $# -ge 2 ]] || die "--split needs a value"; SPLIT="$2"; shift 2 ;;
        --split=*) SPLIT="${1#*=}"; shift ;;
        --mode) [[ $# -ge 2 ]] || die "--mode needs a value"; MODE="$2"; shift 2 ;;
        --mode=*) MODE="${1#*=}"; shift ;;
        --only) [[ $# -ge 2 ]] || die "--only needs a value"; ONLY="$2"; shift 2 ;;
        --only=*) ONLY="${1#*=}"; shift ;;
        --rerun) [[ $# -ge 2 ]] || die "--rerun needs a value"; RERUN="$2"; shift 2 ;;
        --rerun=*) RERUN="${1#*=}"; shift ;;
        --prune-cache) PRUNE=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --) shift; PASSTHROUGH+=("$@"); break ;;
        *) PASSTHROUGH+=("$1"); shift ;;
    esac
done

[[ "$SPLIT" == "dev" || "$SPLIT" == "eval" ]] || die "--split must be dev or eval, got '$SPLIT'"
case "$MODE" in
    "") ;;
    oracle|nop) PASSTHROUGH=(--agent "$MODE" "${PASSTHROUGH[@]+"${PASSTHROUGH[@]}"}") ;;
    *) die "--mode supports oracle|nop; pass model agents after -- (e.g. -- --agent mini-swe-agent --model ...)" ;;
esac

SPLIT_ARGS="configs/${SPLIT}_tasks.args"
TUA_ROOT="data/TUA-Bench"
export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"
# Harbor imports LiteLLM, which otherwise downloads a price list from GitHub on every start.
# We never use those prices (costs come from configs/pricing.json), so use its built-in copy.
export LITELLM_LOCAL_MODEL_COST_MAP="${LITELLM_LOCAL_MODEL_COST_MAP:-True}"
N_CONCURRENT="${N_CONCURRENT:-1}"
MIN_FREE_GB="${MIN_FREE_GB:-10}"
CACHE_KEEP_GB="${CACHE_KEEP_GB:-15}"

[[ -f "$SPLIT_ARGS" ]] || die "no $SPLIT_ARGS; run scripts/sample_tasks.py"
[[ -d "$TUA_ROOT/tasks" ]] || die "missing $TUA_ROOT; see README 'Team setup'"

# Task list for this run: the split, optionally narrowed by --only.
TASKS=()
while read -r flag id; do [[ "$flag" == "-i" ]] && TASKS+=("$id"); done < "$SPLIT_ARGS"
if [[ -n "$ONLY" ]]; then
    wanted=()
    IFS=',' read -r -a wanted <<< "$ONLY"
    for id in "${wanted[@]}"; do
        printf '%s\n' "${TASKS[@]}" | grep -qx "$id" || die "--only: '$id' is not in the $SPLIT split"
    done
    TASKS=("${wanted[@]}")
fi
RERUN_IDS=()
if [[ -n "$RERUN" ]]; then
    IFS=',' read -r -a RERUN_IDS <<< "$RERUN"
    for id in "${RERUN_IDS[@]}"; do
        printf '%s\n' "${TASKS[@]}" | grep -qx "$id" || die "--rerun: '$id' is not in this run's task list"
    done
fi
ARGS_FILE="$(mktemp "${TMPDIR:-/tmp}/harbor_run_args.XXXXXX")"
trap 'rm -f "$ARGS_FILE"' EXIT
for id in "${TASKS[@]}"; do echo "-i $id"; done > "$ARGS_FILE"

# 0. Paid-run gates: free only if the agent is exactly oracle or nop.
agent=""; custom_agent=0; run_id=""; has_env_file=0; HARBOR_ARGS=()
for ((i = 0; i < ${#PASSTHROUGH[@]}; i++)); do
    case "${PASSTHROUGH[i]}" in
        -a|--agent) agent="${PASSTHROUGH[i+1]:-}" ;;
        --agent=*) agent="${PASSTHROUGH[i]#*=}" ;;
        --agent-import-path|--agent-import-path=*) custom_agent=1 ;;
        --env-file|--env-file=*) has_env_file=1 ;;
    esac
    # --job-name names the whole run; each task becomes its own job inside it.
    case "${PASSTHROUGH[i]}" in
        --job-name) run_id="${PASSTHROUGH[i+1]:-}"; i=$((i + 1)); continue ;;
        --job-name=*) run_id="${PASSTHROUGH[i]#*=}"; continue ;;
        --jobs-dir|-o) i=$((i + 1)); continue ;;
        --jobs-dir=*) continue ;;
    esac
    HARBOR_ARGS+=("${PASSTHROUGH[i]}")
done
[[ -n "$agent" || $custom_agent -eq 1 ]] || die "no agent given; use --mode oracle or pass --agent/--agent-import-path after --"
if [[ $custom_agent -eq 1 || ( "$agent" != "oracle" && "$agent" != "nop" ) ]]; then
    [[ "${CONFIRM_PAID:-}" == "1" ]] || die "this run calls a paid model; re-run with CONFIRM_PAID=1 once the cost estimate is agreed"
    if [[ "$SPLIT" == "eval" ]]; then
        [[ "${CONFIRM_EVAL:-}" == "1" ]] || die "paid runs on the eval split are for recorded results only; set CONFIRM_EVAL=1 to proceed"
    fi
fi
# Secrets come from .env (git-ignored). Harbor only reads it via --env-file;
# its keys feed model agents and the verifier env of LLM-judged tasks.
if [[ -f .env && $has_env_file -eq 0 ]]; then
    HARBOR_ARGS+=(--env-file .env)
fi
run_id="${run_id:-${SPLIT}-${MODE:-${agent:-custom}}-$(date +%Y%m%d-%H%M%S)}"
RUN_DIR="jobs/$run_id"

# 1. Benchmark checkout: pinned commit, tasks and verifiers unmodified.
want_sha="$(python3 -c 'import json; print(json.load(open("configs/task_subset.json"))["tua_bench_commit"])')"
have_sha="$(git -C "$TUA_ROOT" rev-parse HEAD)"
[[ "$have_sha" == "$want_sha" ]] || die "TUA-Bench at $have_sha, subset was drawn at $want_sha"
[[ -z "$(git -C "$TUA_ROOT" status --porcelain --untracked-files=no -- tasks dataset.toml)" ]] \
    || die "TUA-Bench tasks/verifiers have local modifications"

# 2. Harbor resolves the task list to exactly the intended tasks.
uv run --frozen python scripts/check_harbor_filter.py "$ARGS_FILE"

# 3. Assets that `setup-env` downloads (inputs, references, test fixtures) exist.
python3 scripts/check_assets.py "$ARGS_FILE"

# 4. Docker VM can fit the largest task at the chosen concurrency
#    (Harbor's own default of 4 concurrent 8 GB trials would OOM a 16 GB Mac).
need_mb="$(python3 - "$ARGS_FILE" <<'EOF'
import json, sys
ids = open(sys.argv[1]).read().split()[1::2]
tasks = json.load(open("configs/task_subset.json"))["tasks"]
print(max(tasks[t]["memory_mb"] for t in ids))
EOF
)"
docker info >/dev/null 2>&1 || die "Docker daemon is not running; start Docker Desktop"
have_mb=$(( $(docker info --format '{{.MemTotal}}') / 1024 / 1024 ))
(( have_mb >= need_mb * N_CONCURRENT )) || die "Docker VM has ${have_mb} MB; this run needs ${need_mb} MB x ${N_CONCURRENT} concurrent. Raise Docker Desktop > Settings > Resources > Memory, or lower N_CONCURRENT."

free_gb() { df -Pk "$ROOT" | awk 'NR==2 {print int($4 / 1048576)}'; }

harbor_cmd() {  # $1 = task id
    CMD=(uv run --frozen harbor run
        -p "$TUA_ROOT/tasks"
        -i "$1"
        --n-concurrent "$N_CONCURRENT"
        --delete
        --jobs-dir "$RUN_DIR"
        --job-name "$1"
        "${HARBOR_ARGS[@]+"${HARBOR_ARGS[@]}"}")
}

say "run=$run_id split=$SPLIT tasks=${#TASKS[@]} agent=${agent:-custom} platform=$DOCKER_DEFAULT_PLATFORM concurrency=$N_CONCURRENT docker_mem=${have_mb}MB free_disk=$(free_gb)GB prune_cache=$PRUNE"
if [[ $DRY_RUN -eq 1 ]]; then
    for id in "${TASKS[@]}"; do harbor_cmd "$id"; printf '%q ' "${CMD[@]}"; echo; done
    exit 0
fi

trap 'echo; say "interrupted; finished tasks are in $RUN_DIR"; exit 130' INT
mkdir -p "$RUN_DIR"
n=0
for id in "${TASKS[@]}"; do
    n=$((n + 1))
    if [[ -d "$RUN_DIR/$id" ]]; then
        # finished | errored (every trial raised an exception) | interrupted (job never finished)
        state="$(python3 - "$RUN_DIR/$id" <<'PYEOF'
import json, sys
from pathlib import Path
job = Path(sys.argv[1])
try:
    finished = json.loads((job / "result.json").read_text()).get("finished_at")
except (OSError, ValueError):
    finished = None
trials = [json.loads(p.read_text()) for p in job.glob("*__*/result.json")]
if not finished:
    print("interrupted")
elif trials and all(t.get("exception_info") for t in trials):
    print("errored")
else:
    print("finished")
PYEOF
)"
        if [[ " ${RERUN_IDS[*]+${RERUN_IDS[*]}} " == *" $id "* ]]; then
            state="rerun"
        fi
        if [[ "$state" == "finished" ]]; then
            say "[$n/${#TASKS[@]}] $id already finished in this run, skipping"
            continue
        fi
        # Harbor would treat an interrupted or errored trial as done on resume, so keep the old
        # attempt aside (logs intact) and start the task fresh.
        aside="$RUN_DIR/$id.$state-$(date +%Y%m%d-%H%M%S)"
        mv "$RUN_DIR/$id" "$aside"
        say "[$n/${#TASKS[@]}] $id: earlier attempt $state; moved to $(basename "$aside") and rerunning"
    fi
    fg=$(free_gb)
    (( fg >= MIN_FREE_GB )) || die "stopping before $id: ${fg} GB free < MIN_FREE_GB=${MIN_FREE_GB}. Free space (or use --prune-cache), then re-run with --job-name $run_id to resume."
    say "[$n/${#TASKS[@]}] $id (free disk ${fg} GB)"
    harbor_cmd "$id"
    "${CMD[@]}" || say "harbor exited non-zero for $id; continuing"
    if [[ $PRUNE -eq 1 ]]; then
        docker builder prune -f --keep-storage "${CACHE_KEEP_GB}GB" >/dev/null || say "build-cache prune failed (continuing)"
        say "build cache pruned to <= ${CACHE_KEEP_GB} GB; free disk $(free_gb) GB"
    fi
done
python3 scripts/summarize_run.py "$RUN_DIR"
