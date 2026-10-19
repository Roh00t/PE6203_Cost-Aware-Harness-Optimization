# Partial C1/C3 dev validation

Code revision: 07934d7, with a local memory-check override in
scripts/harbor_run.sh setting need_mb=7000.

Docker reported 7805 MB. The override bypassed the original
resource preflight; it did not increase available memory.
These results are preliminary and are not a completed parity study.

## Coverage

- C1: 10 attempted, 7 scored, 3 infrastructure/API failures.
- C3: 10 attempted, 8 scored, 2 infrastructure/API failures.
- B0/H0 parity results are not available yet.

## Cost

- C1 known agent table cost: $0.004174632.
- C3 known agent table cost: $0.005874732.
- Each configuration has 9 calls with unknown cost.
- Known costs are lower bounds and exclude verifier charges.

## Observations

- C1 recorded two offload events and no compaction event.
- C3 recorded no cap_reached event.
- Several trials ended with RepeatedFormatError.
- Four trials failed with upstream Darkbloom rate-limit errors.
- C1 task 086 failed during Docker image building.
  The laptop reportedly slept during this trial.

## Trajectory review (2026-10-19)

- Format handling is a prominent failure mode in these runs: each configuration logged 40 `format_error` events. For example, the [C1 task 003 trajectory](h0-c1/003-rebuild-energy-model/003-rebuild-energy-model__gbjbADU/agent/mini-swe-agent.trajectory.json) ends with `RepeatedFormatError` after repeated assistant replies without tool calls.
- The observed component events are sparse: C1's two offloads both occurred in task 009, while C3 recorded no `cap_reached` event. These runs therefore do not establish broad C1 offload or C3 budget-cap behavior.
- C1 has 7 scored trials and C3 has 8. Without matched B0/H0 runs, reward differences cannot be attributed to C1 or C3. Treat these trajectories as debugging evidence, not comparative results.
- Each configuration has nine calls with null token usage. The collector rejects those records rather than pricing them as zero; the published known-cost totals remain lower bounds.

Collector regression coverage is in [`tests/test_collect_costs.py`](../../../tests/test_collect_costs.py). A reporting policy for incomplete-usage calls still needs team agreement; do not infer their cost from these logs.

## Interpretation

Infrastructure failures must not be silently treated as task failures.
The displayed summary means are not final comparison results.
Keep the original failed attempts when adding reruns.

## Remaining work

Resolve resource availability, rerun affected infrastructure failures,
complete B0/H0 comparisons, and finish component validation.
Exports omit some files according to export_run.py filtering.