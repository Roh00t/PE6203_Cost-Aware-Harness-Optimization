"""scripts/summarize_run.py: one row per finished trial, archived attempts left out."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "summarize_run.py"


def trial(run: Path, task_folder: str, trial_id: str, reward: float | None, finished: bool = True) -> None:
    task = task_folder.split(".")[0]
    path = run / task_folder / f"{task}__{trial_id}"
    path.mkdir(parents=True)
    result = {"task_name": f"local/{task}", "trial_name": path.name, "agent_info": {"name": "oracle"},
              "verifier_result": None if reward is None else {"rewards": {"reward": reward}},
              "agent_execution": {"started_at": "2026-10-25T00:00:00Z", "finished_at": "2026-10-25T00:02:00Z"}}
    if finished:
        result["finished_at"] = "2026-10-25T00:03:00Z"
    (path / "result.json").write_text(json.dumps(result))


def summarize(run: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(run)], capture_output=True, text=True)


def test_archived_and_unfinished_attempts_are_ignored(tmp_path):
    trial(tmp_path, "001-a", "keep", 1.0)
    trial(tmp_path, "002-b", "keep", None)  # finished without a reward: listed, not scored (BF-31)
    trial(tmp_path, "001-a.errored-20261026-000759", "old", 0.0)
    trial(tmp_path, "001-a.interrupted-20261026-014159", "old", 0.0)
    trial(tmp_path, "001-a.rerun-20261026-020000", "old", 0.0)
    trial(tmp_path, "003-c", "running", 1.0, finished=False)
    done = summarize(tmp_path)
    assert done.returncode == 0, done.stderr
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert [row["trial"] for row in summary["trials"]] == ["001-a__keep", "002-b__keep"]
    assert summary["mean_reward"] == 1.0
    assert (summary["n_scored"], summary["n_unscored"]) == (1, 1)
    assert summary["trials"][0]["agent_s"] == 120.0
    assert "2 trials, mean reward 1.000 over 1 scored (1 without a reward, not scored)" in done.stdout


def test_folders_without_trial_separator_are_not_trials(tmp_path):
    trial(tmp_path, "001-a", "keep", 1.0)
    (tmp_path / "001-a" / "result.json").write_text(json.dumps({"finished_at": "x"}))  # job-level file
    summary = summarize(tmp_path)
    assert summary.returncode == 0, summary.stderr
    assert len(json.loads((tmp_path / "summary.json").read_text())["trials"]) == 1


def test_run_with_no_finished_trials_fails(tmp_path):
    trial(tmp_path, "001-a.errored-20261026-000759", "old", 0.0)
    done = summarize(tmp_path)
    assert done.returncode != 0 and "no finished trials" in done.stderr
    assert not (tmp_path / "summary.json").exists()
