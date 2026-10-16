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

## Interpretation

Infrastructure failures must not be silently treated as task failures.
The displayed summary means are not final comparison results.
Keep the original failed attempts when adding reruns.

## Remaining work

Resolve resource availability, rerun affected infrastructure failures,
complete B0/H0 comparisons, and finish component validation.
Exports omit some files according to export_run.py filtering.