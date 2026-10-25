"""Offline checks for the configuration set, the C0 prompt and scripts/run_all_configs.py."""

import importlib.util
import sys
from pathlib import Path

import pytest
from jinja2 import StrictUndefined, Template

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.config import load_config  # noqa: E402
from harness.prompts import render_templates  # noqa: E402

spec = importlib.util.spec_from_file_location("run_all_configs", ROOT / "scripts" / "run_all_configs.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_all_eleven_configurations_are_registered_and_exist():
    assert len(runner.ALL) == 11
    for name in runner.ALL:
        path = runner.STOCK.get(name) or runner.HARNESS[name]
        assert (ROOT / path).is_file(), path


@pytest.mark.parametrize("name", list(runner.HARNESS))
def test_harness_configs_load_and_name_themselves(name):
    config, stock = load_config(runner.HARNESS[name])
    assert config.config_id == name
    agent, _ = render_templates(stock, config)
    assert "{{task}}" in agent["instance_template"].replace(" ", "")
    # Only C3 configurations carry the step cap into the loop; baselines stay uncapped.
    assert stock["agent"]["step_limit"] == (50 if config.enabled("C3") else 0)


def test_single_component_ablations_enable_exactly_one_component():
    for n in range(6):
        config, _ = load_config(runner.HARNESS[f"H0+C{n}"])
        assert config.components == [f"C{n}"]


def test_full_variants_differ_only_in_model_and_dollar_cap():
    v, v_stock = load_config(runner.HARNESS["V"])
    ve, ve_stock = load_config(runner.HARNESS["V-E"])
    assert v.components == ve.components == ["C0", "C1", "C2", "C3", "C4", "C5"]
    assert v.plugins == ve.plugins and len(v.plugins) == 3
    assert (v.step_limit, v.command_timeout) == (ve.step_limit, ve.command_timeout) == (50, 180)
    assert v.budget_usd == 0.01 and ve.budget_usd == 0.0167
    assert v_stock["model"]["model_name"] == "openrouter/openai/gpt-oss-20b"
    assert ve_stock["model"]["model_name"] == "openrouter/openai/gpt-oss-120b"


def test_ve_cap_is_the_base_cap_at_expensive_prices():
    import json

    prices = json.loads((ROOT / "configs" / "pricing.json").read_text())["models"]
    base, exp = prices["openai/gpt-oss-20b"], prices["openai/gpt-oss-120b"]
    ratio_in = exp["prompt_usd_per_mtok"] / base["prompt_usd_per_mtok"]
    ratio_out = exp["completion_usd_per_mtok"] / base["completion_usd_per_mtok"]
    assert ratio_in == pytest.approx(ratio_out)
    assert load_config(runner.HARNESS["V-E"])[0].budget_usd == pytest.approx(0.01 * ratio_in, abs=1e-4)


def test_c0_prompt_renders_strictly_and_states_the_tool_call_contract():
    config, stock = load_config(runner.HARNESS["V"])
    agent, variables = render_templates(stock, config)
    text = Template(agent["instance_template"], undefined=StrictUndefined).render(
        task="Example task", **{k: v for k, v in variables.items() if not k.startswith("_")}
    )
    assert "Example task" in text and "{{" not in text
    assert "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" in text
    assert "exactly one tool call" in agent["system_template"]


def test_short_names_and_slugs():
    configs = runner.resolve_configs("B0,C1,V-E")
    assert [c.name for c in configs] == ["B0", "H0+C1", "V-E"]
    assert [c.slug for c in configs] == ["b0", "h0-c1", "v-e"]


def test_unknown_or_duplicate_configs_are_rejected():
    with pytest.raises(SystemExit):
        runner.resolve_configs("B0,B1")
    with pytest.raises(SystemExit):
        runner.resolve_configs("C1,H0+C1")


def test_stock_command_uses_frozen_model_file_and_no_caps():
    (b0,) = runner.resolve_configs("B0")
    cmd = runner.build_command(b0, "dev", "t1", "run1", 0.5, prune_cache=False)
    assert cmd[:6] == ["bash", "scripts/harbor_run.sh", "--split", "dev", "--only", "t1"]
    assert "--agent" in cmd and "mini-swe-agent" in cmd
    assert "config_file=configs/models/base.yaml" in cmd
    assert "version=2.4.6" in cmd
    assert not any(a.startswith("job_budget_usd") for a in cmd)  # stock defaults: no cap


def test_harness_command_carries_config_and_shared_ledger():
    (v,) = runner.resolve_configs("V")
    cmd = runner.build_command(v, "eval", "t1", "run1", 0.5, prune_cache=True)
    assert "--prune-cache" in cmd[: cmd.index("--")]
    assert cmd[cmd.index("--job-name") + 1] == "run1/v"
    assert "config_path=configs/harness/V.yaml" in cmd
    assert "job_budget_usd=0.5" in cmd
    assert f"job_ledger_path={ROOT / 'jobs' / 'run1' / 'ledger.sqlite'}" in cmd
    assert "--ae" not in cmd  # the harness runs on the host from uv.lock


def test_stock_baselines_install_the_pilot_dependency_snapshot():
    # B0/E install mini-swe-agent inside the container; unpinned resolution broke them.
    for config in runner.resolve_configs("B0,E"):
        cmd = runner.build_command(config, "eval", "t1", "run1", None, prune_cache=False)
        env = cmd[cmd.index("--ae") + 1]
        assert env == f"UV_EXCLUDE_NEWER={runner.STOCK_EXCLUDE_NEWER}" == "UV_EXCLUDE_NEWER=2026-10-13"


def test_preflight_blocks_full_variants_until_plugins_exist():
    problems = runner.preflight(runner.resolve_configs("B0,H0,V"))
    blocked = [p for p in problems if p.startswith("V ")]
    plugins_present = (ROOT / "harness" / "components" / "tools.py").is_file()
    assert bool(blocked) != plugins_present
    assert not [p for p in problems if p.startswith(("B0", "H0 "))]
