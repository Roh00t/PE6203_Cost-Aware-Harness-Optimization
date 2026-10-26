"""The frozen subset, its fingerprints and the amendment rule (scripts/task_list.py)."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_list", ROOT / "scripts" / "task_list.py")
task_list = importlib.util.module_from_spec(spec)
spec.loader.exec_module(task_list)

SAMPLED_EVAL = "08cef02483250faee37a4e7d599fe9c8998b8ca256dfeb3de8455babf0687524"
FINAL_EVAL = "973635ea4e6a477e2fbfffd1045494cb69e0678c02ceea2276c56c63fa0468b8"
SUBSET = json.loads((ROOT / "configs" / "task_subset.json").read_text())
AMENDMENTS = json.loads((ROOT / "configs" / "subset_amendments.json").read_text())


def args_ids(name: str) -> list[str]:
    lines = (ROOT / "configs" / name).read_text().split("\n")
    return [line.split(maxsplit=1)[1] for line in lines if line.startswith("-i ")]


def test_sampled_subset_is_unchanged():
    assert SUBSET["eval_fingerprint"] == SAMPLED_EVAL
    assert task_list.fingerprint(SUBSET["eval_task_ids"]) == SAMPLED_EVAL
    assert task_list.fingerprint(args_ids("eval_tasks.args")) == SAMPLED_EVAL
    assert task_list.fingerprint(SUBSET["dev_task_ids"]) == SUBSET["dev_fingerprint"]
    assert task_list.fingerprint(args_ids("dev_tasks.args")) == SUBSET["dev_fingerprint"]


def test_amended_eval_split_has_the_final_fingerprint():
    assert AMENDMENTS["frozen"] is True
    eval_ids, unused = task_list.apply_amendments(SUBSET, AMENDMENTS["amendments"])
    assert task_list.fingerprint(eval_ids) == FINAL_EVAL == AMENDMENTS["final_eval_fingerprint"]
    assert len(eval_ids) == len(set(eval_ids)) == 40
    assert not set(eval_ids) & set(SUBSET["dev_task_ids"])
    for amendment in AMENDMENTS["amendments"]:
        assert amendment["removed"] not in eval_ids and amendment["added"] in eval_ids
        assert amendment["added"] not in unused[amendment["family"]]


def test_fingerprint_ignores_order():
    ids = SUBSET["eval_task_ids"]
    assert task_list.fingerprint(list(reversed(ids))) == task_list.fingerprint(ids)


def test_cli_prints_the_final_eval_fingerprint():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "task_list.py"), "eval", "--fingerprint"],
                          capture_output=True, text=True, check=True)
    assert done.stdout.strip() == FINAL_EVAL


def test_cli_reserve_list_leaves_out_consumed_reserves():
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "task_list.py"), "reserve"],
                          capture_output=True, text=True, check=True)
    reserves = done.stdout.split()
    consumed = {a["added"] for a in AMENDMENTS["amendments"]}
    assert reserves and not consumed & set(reserves)
    assert not set(reserves) & set(SUBSET["eval_task_ids"] + SUBSET["dev_task_ids"])


def first_amendment() -> dict:
    return copy.deepcopy(AMENDMENTS["amendments"][0])


def test_amendment_that_skips_the_next_reserve_is_refused():
    amendment = first_amendment()
    family = SUBSET["families"][amendment["family"]]
    assert amendment["added"] == family["reserve"][0]
    amendment["added"] = family["reserve"][1]
    with pytest.raises(SystemExit, match="next reserve for .* is " + family["reserve"][0]):
        task_list.apply_amendments(SUBSET, [amendment])


def test_reserve_cannot_be_used_twice():
    amendment = first_amendment()
    family = SUBSET["families"][amendment["family"]]
    other = next(t for t in SUBSET["eval_task_ids"]
                 if SUBSET["tasks"][t]["family"] == amendment["family"] and t != amendment["removed"])
    again = {**amendment, "removed": other}
    with pytest.raises(SystemExit, match="next reserve for .* is " + family["reserve"][1]):
        task_list.apply_amendments(SUBSET, [amendment, again])


@pytest.mark.parametrize("change, message", [
    ({"family": "Web & Information" + "?"}, "is in family"),
    ({"removed": SUBSET["dev_task_ids"][0]}, "is not in the eval split"),
    ({"evidence": None}, "missing fields"),
])
def test_invalid_amendments_are_refused(change, message):
    amendment = {**first_amendment(), **change}
    amendment = {k: v for k, v in amendment.items() if v is not None}
    with pytest.raises(SystemExit, match=message):
        task_list.apply_amendments(SUBSET, [amendment])


def test_apply_amendments_does_not_mutate_the_frozen_subset():
    before = copy.deepcopy(SUBSET)
    task_list.apply_amendments(SUBSET, AMENDMENTS["amendments"])
    assert SUBSET == before


@pytest.mark.skipif(not (ROOT / "data" / "TUA-Bench" / "tasks").is_dir(),
                    reason="data/TUA-Bench is not checked out (README 'Team Setup')")
def test_sampling_reproduces_the_sampled_fingerprint(tmp_path):
    done = subprocess.run([sys.executable, str(ROOT / "scripts" / "sample_tasks.py"), "--out-dir", str(tmp_path)],
                          capture_output=True, text=True, check=True)
    assert f"eval fingerprint {SAMPLED_EVAL}" in done.stdout
    assert json.loads((tmp_path / "task_subset.json").read_text())["eval_task_ids"] == SUBSET["eval_task_ids"]
