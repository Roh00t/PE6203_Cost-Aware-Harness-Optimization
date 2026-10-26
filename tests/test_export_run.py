"""What scripts/export_run.py copies from jobs/ into results/, and what it refuses."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "export_run.py"
spec = importlib.util.spec_from_file_location("export_run", SCRIPT)
export_run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_run)


def finished_trial(run: Path, task: str = "001-task") -> Path:
    trial = run / task / f"{task}__abc"
    (trial / "agent").mkdir(parents=True)
    (trial / "verifier").mkdir()
    (trial / "result.json").write_text(json.dumps({
        "task_name": f"local/{task}", "trial_name": f"{task}__abc", "finished_at": "2026-10-25T00:00:00Z",
        "agent_info": {"name": "oracle"}, "verifier_result": {"rewards": {"reward": 1.0}}}))
    (trial / "verifier" / "reward.txt").write_text("1.0")
    return trial


def write(path: Path, data: bytes | str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode() if isinstance(data, str) else data)


def export(src: Path, dest: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(src), str(dest)], capture_output=True, text=True)


def test_wanted_rule():
    limit = export_run.MAX_BYTES
    assert export_run.wanted(Path("t/t__a/agent/trajectory.json"), limit)
    assert not export_run.wanted(Path("t/t__a/agent/trajectory.json"), limit + 1)
    assert export_run.wanted(Path("t/t__a/artifacts/answer.txt"), 10)
    assert not export_run.wanted(Path("t/t__a/artifacts/screenshot.png"), 10)
    assert not export_run.wanted(Path("t/t__a/artifacts/profile/Default/Preferences"), 10)
    assert not export_run.wanted(Path("t/t__a/artifacts/profile/Local State"), 10)
    assert not export_run.wanted(Path("t/t__a/artifacts/profile/Default/Cookies"), 10)


def test_export_keeps_logs_and_leaves_out_large_files_and_browser_profiles(tmp_path):
    src, dest = tmp_path / "jobs" / "run", tmp_path / "results" / "run"
    trial = finished_trial(src)
    write(trial / "agent" / "calls.jsonl", "{}\n")
    write(trial / "verifier" / "test-stdout.txt", "1 passed\n")
    write(trial / "artifacts" / "active_url.txt", "https://example.org\n")
    write(trial / "artifacts" / "state.json", "{}")
    write(trial / "agent" / "exactly-2mb.log", b"a" * export_run.MAX_BYTES)
    write(trial / "agent" / "huge.log", b"a" * (export_run.MAX_BYTES + 1))
    write(trial / "artifacts" / "big.json", b"{}" + b" " * export_run.MAX_BYTES)
    write(trial / "artifacts" / "screenshot.png", b"\x89PNG")
    for name in ("Default/Preferences", "Default/Cookies", "Local State", "Default/History"):
        write(trial / "artifacts" / "chrome-profile" / name)

    done = export(src, dest)
    assert done.returncode == 0, done.stderr
    copied = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    assert copied == [
        "001-task/001-task__abc/agent/calls.jsonl",
        "001-task/001-task__abc/agent/exactly-2mb.log",
        "001-task/001-task__abc/artifacts/active_url.txt",
        "001-task/001-task__abc/artifacts/state.json",
        "001-task/001-task__abc/result.json",
        "001-task/001-task__abc/verifier/reward.txt",
        "001-task/001-task__abc/verifier/test-stdout.txt",
        "summary.json",
    ]
    assert "skipped 7" in done.stdout  # 2 over 2 MB, 1 image, 4 profile files
    assert json.loads((src / "summary.json").read_text())["mean_reward"] == 1.0


def test_export_refuses_files_that_look_like_api_keys(tmp_path):
    src, dest = tmp_path / "jobs" / "run", tmp_path / "results" / "run"
    trial = finished_trial(src)
    write(trial / "agent" / "trial.log", "OPENROUTER_API_KEY=sk-or-v1-" + "0123456789abcdef" * 4 + "\n")
    done = export(src, dest)
    assert done.returncode != 0
    assert "possible API key" in done.stderr and "trial.log" in done.stderr
    assert not dest.exists()


def test_export_rejects_a_missing_run(tmp_path):
    done = export(tmp_path / "nope", tmp_path / "out")
    assert done.returncode != 0 and "no such run" in done.stderr
