#!/usr/bin/env bash
# Run Harbor on the locked TUA-Bench subset with safe local defaults.
#
#   scripts/harbor_run.sh --split dev --mode oracle          # free: reference solutions
#   scripts/harbor_run.sh --split eval --mode oracle --dry-run
#   CONFIRM_PAID=1 scripts/harbor_run.sh --split dev -- --agent mini-swe-agent --model openrouter/<id>
#
# Options (before any Harbor arguments):
#   --split dev|eval   task split (default: eval; env SPLIT also works)
#   --mode oracle|nop  shorthand for `--agent oracle|nop`
#   --dry-run          run the pre-flight checks, print the Harbor command, exit
#   --                 everything after this is passed to `harbor run` unchanged
# Unrecognised options are also passed through to `harbor run`.
#
# Pre-flight checks refuse to start if the checkout, subset or Docker VM is
# wrong. Paid runs (any agent other than oracle/nop) need CONFIRM_PAID=1, and
# paid runs on the eval split also need CONFIRM_EVAL=1 (guardrails.md §4).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

die() { echo "harbor_run: $*" >&2; exit 1; }

SPLIT="${SPLIT:-eval}"
MODE=""
DRY_RUN=0
PASSTHROUGH=()
while (($#)); do
    case "$1" in
        --split) [[ $# -ge 2 ]] || die "--split needs a value"; SPLIT="$2"; shift 2 ;;
        --split=*) SPLIT="${1#*=}"; shift ;;
        --mode) [[ $# -ge 2 ]] || die "--mode needs a value"; MODE="$2"; shift 2 ;;
        --mode=*) MODE="${1#*=}"; shift ;;
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

ARGS_FILE="configs/${SPLIT}_tasks.args"
TUA_ROOT="data/TUA-Bench"
export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"
N_CONCURRENT="${N_CONCURRENT:-1}"

[[ -f "$ARGS_FILE" ]] || die "no $ARGS_FILE; run scripts/sample_tasks.py"
[[ -d "$TUA_ROOT/tasks" ]] || die "missing $TUA_ROOT; see README 'Evaluation Subset > Reproduce'"

# 0. Paid-run gates: free only if the agent is exactly oracle or nop.
agent=""; custom_agent=0; has_job_name=0; has_env_file=0
for ((i = 0; i < ${#PASSTHROUGH[@]}; i++)); do
    case "${PASSTHROUGH[i]}" in
        -a|--agent) agent="${PASSTHROUGH[i+1]:-}" ;;
        --agent=*) agent="${PASSTHROUGH[i]#*=}" ;;
        --agent-import-path|--agent-import-path=*) custom_agent=1 ;;
        --job-name|--job-name=*) has_job_name=1 ;;
        --env-file|--env-file=*) has_env_file=1 ;;
    esac
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
    PASSTHROUGH+=(--env-file .env)
fi
if [[ $has_job_name -eq 0 ]]; then
    PASSTHROUGH+=(--job-name "${SPLIT}-${MODE:-${agent:-custom}}-$(date +%Y%m%d-%H%M%S)")
fi

# 1. Benchmark checkout: pinned commit, tasks and verifiers unmodified.
want_sha="$(python3 -c 'import json; print(json.load(open("configs/task_subset.json"))["tua_bench_commit"])')"
have_sha="$(git -C "$TUA_ROOT" rev-parse HEAD)"
[[ "$have_sha" == "$want_sha" ]] || die "TUA-Bench at $have_sha, subset was drawn at $want_sha"
[[ -z "$(git -C "$TUA_ROOT" status --porcelain --untracked-files=no -- tasks dataset.toml)" ]] \
    || die "TUA-Bench tasks/verifiers have local modifications"

# 2. Harbor resolves the args file to exactly the intended tasks.
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
(( have_mb >= need_mb * N_CONCURRENT )) || die "Docker VM has ${have_mb} MB; ${SPLIT} split needs ${need_mb} MB x ${N_CONCURRENT} concurrent. Raise Docker Desktop > Settings > Resources > Memory, or lower N_CONCURRENT."

# --no-delete keeps built task images, so later configurations reuse them
# instead of rebuilding (Harbor's default --delete runs `down --rmi all`).
# shellcheck disable=SC2046  # word-splitting the args file is intended
CMD=(uv run --frozen harbor run
    -p "$TUA_ROOT/tasks"
    $(cat "$ARGS_FILE")
    --n-concurrent "$N_CONCURRENT"
    --no-delete
    --jobs-dir jobs
    "${PASSTHROUGH[@]}")

echo "harbor_run: split=$SPLIT agent=${agent:-custom} platform=$DOCKER_DEFAULT_PLATFORM concurrency=$N_CONCURRENT docker_mem=${have_mb}MB"
if [[ $DRY_RUN -eq 1 ]]; then
    printf '%q ' "${CMD[@]}"; echo
    exit 0
fi
exec "${CMD[@]}"
