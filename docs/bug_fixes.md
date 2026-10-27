# Bug fixes (branch `bug-fixes`, harness-v1.1)

This file tracks the fixes for every bug from the whole-repo review of 2026-10-27:
- bugs #1–#9 from `docs/harness_bug_review.md`;
- the new bugs from the four-area review (harness core, components and guardrails, analysis scripts, run tooling);
- the wrong statements in the results text.

**Status: pending Rohit's approval (freeze exception).** These changes touch frozen paths: `harness/**`, `scripts/**`, `tests/**`, `configs/**`. They stay uncommitted on `bug-fixes` until Rohit reviews the PR.

**Versioning.** Fixes marked *v1.1* change what the agent sees or which commands run. The eval results in `results/eval/rohit-eval-pass1/` were produced with **harness-v1** (`6c87103`) and are not rerun. The report keeps saying pass 1 used v1. If merged, tag the merge `harness-v1.1`.

Legend: ✅ fixed and tested · 🟡 in progress · ⬜ open.

## Harness (v1.1: behaviour changes)

| ID | Bug | Files | Status | Test |
|---|---|---|---|---|
| BF-01 | U-FMT-03 rejects valid heredocs, `<<` operators and nested `bash -c "…PY"` (review #1) | `harness/guardrails.py` | ✅ | test_known_issues.py::test_valid_commands_are_not_rejected_as_unterminated_heredocs (6) |
| BF-02 | U-INT-04 matches `~/.ssh` paths and `ssh-keygen` (review #2) | `harness/guardrails.py` | ✅ | test_known_issues.py::test_ssh_paths_and_tools_are_not_password_prompts (3) |
| BF-03 | U-INT-03 blocks piped input such as `… \| python3` (review #3) | `harness/guardrails.py` | ✅ | test_known_issues.py::test_piped_interpreter_is_allowed (2) |
| BF-04 | C5 marks unchanged inputs ✗, truncates `.code-workspace`, drops `~` (review #4) | `harness/components/submit_gate.py` | ✅ | test_known_issues.py::test_hyphenated_extension_is_kept, test_home_relative_path_is_not_turned_into_a_root_path, test_gate_does_not_call_an_existing_input_missing |
| BF-05 | Unbilled 429 attempts keep their reservation against B_task and the job ledger (review #5) | `harness/gateway.py` | ✅ | test_known_issues.py::test_rate_limited_attempts_do_not_exhaust_the_task_budget (+ 5xx control) |
| BF-06 | C2 file tools skip the always-on G-rules, G-INT-01 included (review #6) | `harness/loop.py` | ✅ | test_known_issues.py::test_file_tool_cannot_read_grader_paths |
| BF-07 | C4 blocks a repeated probe forever, even after the state changed (review #7) | `harness/components/recovery.py` | ✅ | test_known_issues.py::test_probe_runs_again_after_a_state_change (3) |
| BF-08 | C1 offload overwrites `harness_chars` added earlier by C2/C4 (review #8) | `harness/components/context.py` | ✅ | test_known_issues.py::test_offload_keeps_earlier_harness_chars |
| BF-09 | C3 status line prints V-E's $0.0167 as `$0.02` (review #9) | `harness/components/budget.py` | ✅ | test_known_issues.py::test_status_line_shows_the_exact_budget |
| BF-10 | A failed container call crashes the whole trial; stock returns an error observation | `harness/environment.py` | ✅ | test_bug_fixes.py::test_container_call_failure_returns_an_observation, test_cancelled_trial_still_raises |
| BF-11 | Gateway gives up on 429/5xx after about 14 s with no jitter; stock retries for minutes (crashed V-E 011 and 077) | `harness/gateway.py` | ✅ | test_bug_fixes.py::test_rate_limit_retries_back_off_for_minutes_with_jitter, test_rate_limit_still_gives_up_after_the_last_attempt; test_harness_core.py::test_retry_each_attempt_logged updated |
| BF-12 | G-DST-04 blocks the bare words "shutdown"/"reboot" anywhere, e.g. `logging.shutdown()`, even in H0 | `harness/guardrails.py` | ✅ | test_guardrails.py::test_power_commands_only_in_command_position_bf12 |
| BF-13 | G-DST-01 allows `rm -rf /app`, `rm -r -f /`, `rm -rf ~/*` and similar | `harness/guardrails.py` | ✅ | test_guardrails.py::test_recursive_delete_of_roots_in_any_form_bf13 |
| BF-14 | Log-only G-SEC-01 hides any later block; its pattern also matches `${MAX_TOKENS}` | `harness/guardrails.py` | ✅ | test_guardrails.py::test_log_rule_never_hides_a_block_bf14 |
| BF-15 | G-INT-01 misses `ls /tests;` and blocks `ls ~/tests` | `harness/guardrails.py` | ✅ | test_guardrails.py::test_grader_paths_with_separators_but_not_home_folders_bf15 |
| BF-16 | C2 `read_file`/`search` fail on non-UTF-8 files; one unreadable file aborts the whole `search` | `harness/components/tools.py` | ✅ | test_bug_fixes.py::test_search_survives_unreadable_and_non_utf8_files, test_read_file_shows_invalid_bytes_instead_of_failing |
| BF-17 | C2 `edit_file` converts CRLF to LF and counts overlapping matches wrongly | `harness/components/tools.py` | ✅ | test_bug_fixes.py::test_edit_file_keeps_crlf_line_endings, test_edit_file_rejects_overlapping_matches |
| BF-18 | A lone surrogate in C2 arguments crashes the trial | `harness/components/tools.py` | ✅ | test_bug_fixes.py::test_unpaired_surrogate_is_a_tool_error_not_a_crash |
| BF-19 | C5's "90 % of steps" exception assumes 50 steps even when C3 is off | `harness/components/submit_gate.py` | ✅ | test_bug_fixes.py::test_gate_fires_late_in_a_run_without_a_step_cap |
| BF-20 | Ignored extra tool calls run the after-execute hooks: false C4 stall nudges, C3 status lines on every ignored call | `harness/loop.py` | ✅ | test_bug_fixes.py::test_ignored_extra_calls_cause_no_stall_nudge_or_status_line |
| BF-21 | C1 shortening sets `harness_chars = 29` (text is 30 chars) and overwrites earlier counts | `harness/components/context.py` | ✅ | test_bug_fixes.py::test_shortening_counts_its_own_text_and_drops_cut_harness_text |
| BF-22 | Smaller rule slips: U-INT-01 (`top -b`, `watch-files.sh`, indented `vim`), U-INT-02 (`tail -F`, `journalctl --follow`, bounded `timeout … tail -f`), U-FMT-04 (checks heredoc bodies, rejects quoted `echo`), G-DST-02 (`of=/dev/null`) | `harness/guardrails.py` | ✅ | test_guardrails.py::test_interactive_and_follow_rule_edges_bf22, test_submit_rule_ignores_heredoc_bodies_and_quotes_bf22, test_dd_to_pseudo_devices_is_allowed_bf22 |

## Run tooling

| ID | Bug | Files | Status | Test |
|---|---|---|---|---|
| BF-23 | Resuming a run re-runs agent-timeout trials the verifier already scored | `scripts/harbor_run.sh` | ✅ | test_tooling_fixes.py::test_resume_state (7), test_unfinished_job_is_interrupted, test_harbor_run_uses_the_tested_classifier |
| BF-24 | Arguments after `--` override the gates (eval task without `CONFIRM_EVAL`, checkout and memory checks) | `scripts/harbor_run.sh` | ✅ | test_tooling_fixes.py::test_gate_bypassing_arguments_are_refused (11) |
| BF-25 | "Benchmark unmodified" check ignores new untracked files | `scripts/harbor_run.sh`, `scripts/sample_tasks.py` | ✅ | test_tooling_fixes.py::test_checkout_check_includes_untracked_files (2) |
| BF-26 | Leak checker skips `configs/models/*.yaml` (templates reach the model) and non-UTF-8 files | `scripts/check_no_task_leak.py` | ✅ | test_tooling_fixes.py::test_task_id_in_a_model_template_is_a_leak, test_task_id_in_a_latin1_file_is_a_leak |
| BF-27 | Documented eval checks run against the pre-amendment `configs/eval_tasks.args` | `CLAUDE.md`, `README.md`, `docs/STATUS.md` | ✅ | test_tooling_fixes.py::test_args_output_is_the_amended_eval_list |
| BF-28 | A damaged `result.json` aborts the whole run; Ctrl+C leaves Harbor running orphaned | `scripts/harbor_run.sh`, `scripts/run_all_configs.py` | ✅ | test_tooling_fixes.py::test_ctrl_c_waits_for_the_child_trap (2), test_trial_outcome_skips_a_damaged_result, test_resume_state[damaged-json] |
| BF-29 | Nothing checks the frozen fingerprints at run time | `scripts/task_list.py` | ✅ | test_tooling_fixes.py::test_edited_subset_is_refused |
| BF-30 | `export_run.py` follows symlinks and exports images outside `artifacts/` | `scripts/export_run.py` | ✅ | test_tooling_fixes.py::test_export_skips_symlinks_and_images_outside_artifacts |
| BF-31 | `summarize_run.py` scores infrastructure failures as 0 (and fails on Python 3.9) | `scripts/summarize_run.py` | ✅ | test_summarize_run.py::test_archived_and_unfinished_attempts_are_ignored (updated) |
| BF-32 | `analyze.py` drops verifier-scored trials that also raised; cost cross-check tolerance ($0.01) too loose | `scripts/analyze.py`, `scripts/collect_costs.py` | ✅ | test_tooling_fixes.py::test_agent_timeout_with_a_reward_is_scored, test_infrastructure_exception_is_not_scored, test_cross_check_allows_one_late_call_only |
| BF-33 | Nothing tests `harbor_run.sh` (gates, resume, `--rerun`) | `tests/` | ✅ | tests/test_tooling_fixes.py (resume, gates, Ctrl+C); classifier moved to scripts/run_state.py |

## Analysis and results text

| ID | Bug | Files | Status | Test |
|---|---|---|---|---|
| BF-34 | "Harness overhead" also counts the stock format-error feedback (H0 charged $0.0030 with no components) | `harness/gateway.py`, `harness/telemetry.py`, `scripts/collect_costs.py`, results text | ✅ | test_tooling_fixes.py::test_v1_logs_move_format_error_feedback_out_of_harness, test_v1_1_logs_record_feedback_under_its_own_origin |
| BF-35 | README: "V gains less than C0, C2 or C3 alone" is false for C3 | `results/eval/rohit-eval-pass1/README.md`, `docs/report_tasks.md` | ✅ | text: README.md:64, report_tasks.md key message 4 |
| BF-36 | H0+C0 cost marked "≈" but it is a lower bound ("≥") | same | ✅ | text: README.md ablation table, report_tasks.md fact sheet |
| BF-37 | "No single ablation is significant" — C0's interval just excludes zero | same | ✅ | text: README.md:64, report_tasks.md key message 4 |
| BF-38 | Failure counts cover pass 1 only; report prompts point to a non-existent `results/eval/…/failures/` | `results/analysis/eval/rohit-eval-pass1/failures/`, `docs/report_tasks.md` | ✅ | failures/ regenerated for all 11 configs (pass-1 rows byte-identical); prompt paths in report_tasks.md |
| BF-39 | README archived-attempt table says 19 `mcp` crashes and 1 rate-limit crash (actual 18 and 2) | `results/eval/rohit-eval-pass1/README.md` | ✅ | text: README.md archived-attempt table (checked against all 28 archived result.json) |
| BF-40 | C0's reward and call figures compare 38 tasks with H0's 40 | `results/eval/rohit-eval-pass1/README.md`, `docs/report_tasks.md` | ✅ | text: README.md:64, report_tasks.md fact sheet (H0 on the same 38 tasks: 0.120, 470 calls) |

## Log

Tests at the start (`main` at `e7e9978`): `uv run --frozen pytest -q tests`: 201 passed, 21 xfailed.
- **Guardrails (BF-01, 02, 03, 12, 13, 14, 15, 22).** `harness/guardrails.py`, `guardrails.md` §3 kept in sync. A replay of all 3,094 eval bash commands through the fixed rules blocks only V-E/074 (submit chained after `zip`, a correct block) and logs the same 3 `sudo` calls; the other 15 eval blocks (13 U-FMT-03, 1 U-INT-03, 1 U-FMT-04) were false positives and now pass. Tests: 219 passed, 10 xfailed.
- **Components and loop (BF-04, 06, 07, 08, 09, 19, 20, 21).** #4–#9 applied as proposed in `docs/harness_bug_review.md`; their strict-xfail tests now pass and the markers are removed. New tests for BF-19–21 in `tests/test_bug_fixes.py` fail on the v1 code and pass on v1.1. Tests: 232 passed, 1 xfailed (#5, next).
- **Gateway, container adapter, C2 helper (BF-05, 10, 11, 16, 17, 18).** All 21 strict-xfail tests from the bug review now pass. `guardrails.md` §4 updated for the retry policy and the 429 reservation. Cancellation now raises `TrialCancelled` (a `RuntimeError` subclass, same message), so it is never turned into an observation.
- **Run tooling (BF-23 to BF-33).** The resume classifier moved from an inline heredoc in `harbor_run.sh` to `scripts/run_state.py` (Python 3.9-safe, tested). `task_list.py` gained `--args` (the amended eval list as Harbor arguments) and checks the frozen fingerprints on every call. Documented eval checks in `CLAUDE.md`, `README.md`, `docs/STATUS.md` and the two check scripts now use the amended list; `README.md`'s sampling section still checks the sampled list, which is correct there. Running `summarize_run.py` on `jobs/smoke-roshan-paid/b0` during testing regenerated that run's `summary.json` (git-ignored).
- **Overhead (BF-34).** v1.1 logs format-error feedback under its own `feedback` origin. For the committed v1 logs, `collect_costs.py` rebuilds per step how much feedback each prompt held (from the trajectory) and moves it out of "harness". Re-analysis of `results/eval/rohit-eval-pass1`: H0's overhead is now $0 (it has no components); V $0.0082 → $0.0061 (17.3 % → 12.9 % of known cost); V-E $0.0151 → $0.0126 (16.4 % → 13.7 %). Every other number in `summary.csv`, `comparisons.csv`, `ablations.csv`, `families.csv`, `coverage.csv` and both Pareto files is unchanged. The committed `summary.csv`, `trials.csv` and `analysis.json` were patched in place: only `harness_injected_cost_usd_estimate` changed and `format_error_feedback_cost_usd_estimate` was added; all other fields are byte-identical.
- **Results text (BF-35 to BF-40)** corrected in `results/eval/rohit-eval-pass1/README.md` and the fact sheet in `docs/report_tasks.md`, with each change dated and pointing here. `docs/report_drafts/10_discussion.md` uses the corrected figures. `failures/` was regenerated for all 11 configurations: the pass-1 rows are byte-identical, and the six ablation configurations are added (438 scored trials; harness-level 297, model-level 65).
- **Records.** `guardrails.md` §7.2 (eval-phase review and the v1.1 rule changes), `CLAUDE.md` (fifth freeze exception, pending), and status notes at the top of `docs/harness_bug_review.md` and `docs/guardrail_eval_review.md`.

**Final verification (2026-10-27, macOS):**
- `uv run --frozen pytest -q tests`: 277 passed, 0 xfailed (was 201 passed, 21 xfailed).
- `check_no_task_leak.py`: OK (now also scans `configs/models/`).
- Sampled fingerprint `08cef024…` and final eval fingerprint `973635ea…` reproduced.
- `check_harness.py --config` V and V-E: OK.
- `harbor_run.sh --split eval --mode oracle --dry-run`: Harbor resolves exactly 40 tasks and assets are OK.
- The scripts `harbor_run.sh` runs with the system `python3` compile under Python 3.9.
- No paid calls and no Harbor runs.
