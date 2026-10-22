"""Offline plotting-policy tests; no model calls or live benchmark execution."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("plot_under_test", ROOT / "scripts/plot_pareto.py")
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)


def row(config="B0", cost="0.01", reward=0.5, **changes):
    return {"config_id": config, "n_active_trials": 2, "n_attempted_tasks": 2,
            "n_scored_tasks": 2, "scored_task_ids": ["t1", "t2"],
            "attempted_task_ids": ["t1", "t2"], "usage_complete": True,
            "mean_reward_observed": reward, "mean_cost_per_attempted_task_usd": cost,
            "known_cost_observed_usd": str(float(cost) * 2),
            "n_unknown_calls": 0, "n_missing_call_logs": 0, **changes}


def data(*rows):
    return {"metadata": {"split": "dev", "expected_task_ids": ["t1", "t2"]},
            "summary": list(rows)}


def test_lower_bound_is_never_frontier_eligible():
    points, _ = plot.prepare_points(data(row(usage_complete=False,
        mean_cost_per_attempted_task_usd=None, n_unknown_calls=2)))
    assert points[0]["cost_is_lower_bound"] is True
    assert points[0]["frontier_eligible"] is False
    assert plot.frontier(points) == []


def test_partial_reward_coverage_is_excluded_even_with_exact_cost():
    points, _ = plot.prepare_points(data(row(n_scored_tasks=1, scored_task_ids=["t1"])))
    assert points[0]["cost_is_lower_bound"] is False
    assert points[0]["frontier_eligible"] is False


def test_frontier_rejects_strictly_dominated_configurations():
    points, _ = plot.prepare_points(data(row("B0", "0.01", 0.5),
        row("E", "0.02", 0.4), row("V", "0.02", 0.8)))
    assert set(plot.frontier(points)) == {"B0", "V"}


def test_equal_cost_prefers_higher_reward():
    points, _ = plot.prepare_points(data(row("B0", "0.01", 0.2), row("V", "0.01", 0.5)))
    assert plot.frontier(points) == ["V"]


def test_tied_coordinates_keep_both_configurations():
    points, _ = plot.prepare_points(data(row("B0"), row("V")))
    assert set(plot.frontier(points)) == {"B0", "V"}


def test_one_exact_point_does_not_establish_a_comparison_frontier():
    points, _ = plot.prepare_points(data(row()))
    assert plot.frontier(points) == []


def test_unrun_configuration_is_skipped_not_plotted_at_zero():
    points, skipped = plot.prepare_points(data(row(), row("V", n_active_trials=0)))
    assert len(points) == 1
    assert skipped == [{"config_id": "V", "reason": "not_run"}]


def test_all_unscored_input_has_no_plottable_data():
    with pytest.raises(ValueError, match="No observations"):
        plot.prepare_points(data(row(mean_reward_observed=None, n_scored_tasks=0)))


def test_repeated_trials_need_cost_normalization_before_frontier():
    points, _ = plot.prepare_points(data(row(n_active_trials=4)))
    assert "repeated_trials_need_cost_normalization" in points[0]["ineligible_reasons"]


@pytest.mark.parametrize("cost", ["NaN", "-1", "Infinity"])
def test_invalid_cost_is_rejected(cost):
    with pytest.raises(ValueError):
        plot.prepare_points(data(row(mean_cost_per_attempted_task_usd=cost)))


def test_render_exports_plot_and_auditable_policy(tmp_path):
    pytest.importorskip("matplotlib")
    partial = data(
        row("H0+C1", usage_complete=False, n_scored_tasks=1,
            scored_task_ids=["t1"], mean_cost_per_attempted_task_usd=None),
        row("H0+C3", usage_complete=False, mean_cost_per_attempted_task_usd=None),
    )
    result = plot.render(partial, tmp_path / "pareto")
    assert (tmp_path / "pareto.png").read_bytes().startswith(b"\x89PNG")
    assert "<svg" in (tmp_path / "pareto.svg").read_text()
    saved = json.loads((tmp_path / "pareto.json").read_text())
    assert saved["frontier_config_ids"] == []
    assert any("task sets differ" in note for note in saved["notes"])
    assert all(p["cost_is_lower_bound"] for p in result["points"])
