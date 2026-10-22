#!/usr/bin/env python3
"""Plot analysis.json, explicitly separating partial observations and exact costs.

Only complete, exact-cost configurations on the full requested task set are
eligible for the frontier. Incomplete-cost observations have hollow markers
and rightward arrows: their horizontal coordinates are lower bounds.
"""
import argparse
import json
import math
from pathlib import Path


def finite_number(value, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {label}")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid {label}")
    return number


def prepare_points(data: dict) -> tuple[list[dict], list[dict]]:
    expected = set(data["metadata"]["expected_task_ids"])
    if not expected:
        raise ValueError("Expected task list is empty")
    points, skipped = [], []
    seen = set()
    for row in data["summary"]:
        config = row["config_id"]
        if config in seen:
            raise ValueError(f"Duplicate configuration: {config}")
        seen.add(config)
        if not row["n_active_trials"]:
            skipped.append({"config_id": config, "reason": "not_run"})
            continue
        reward = row.get("mean_reward_observed")
        if reward is None:
            skipped.append({"config_id": config, "reason": "no_scored_tasks"})
            continue
        reward = finite_number(reward, "reward")
        if reward > 1:
            raise ValueError("Reward must be between zero and one")
        attempts = row["n_attempted_tasks"]
        if type(attempts) is not int or attempts <= 0:
            raise ValueError("Invalid attempted-task count")
        if row.get("usage_complete") and row.get("mean_cost_per_attempted_task_usd") is not None:
            cost = finite_number(row["mean_cost_per_attempted_task_usd"], "cost")
            lower_bound = False
        else:
            known = row.get("known_cost_observed_usd")
            if known is None:
                skipped.append({"config_id": config, "reason": "no_known_cost"})
                continue
            cost = finite_number(known, "known cost") / attempts
            lower_bound = True
        full = (set(row["scored_task_ids"]) == expected
                and set(row["attempted_task_ids"]) == expected)
        single_trial = row["n_active_trials"] == attempts
        reasons = []
        if lower_bound:
            reasons.append("incomplete_cost")
        if not full:
            reasons.append("incomplete_reward_coverage")
        if not single_trial:
            reasons.append("repeated_trials_need_cost_normalization")
        points.append({
            "config_id": config, "mean_reward": reward,
            "mean_cost_per_attempted_task_usd": cost,
            "cost_is_lower_bound": lower_bound,
            "n_scored_tasks": row["n_scored_tasks"], "n_expected_tasks": len(expected),
            "n_attempted_tasks": attempts,
            "n_unknown_calls": row.get("n_unknown_calls"),
            "n_missing_call_logs": row.get("n_missing_call_logs", 0),
            "frontier_eligible": not reasons, "ineligible_reasons": reasons,
        })
    if not points:
        raise ValueError("No observations have both a scored reward and a known cost")
    return points, skipped


def frontier(points: list[dict]) -> list[str]:
    eligible = [p for p in points if p["frontier_eligible"]]
    if len(eligible) < 2:
        return []
    result = []
    for point in eligible:
        x, y = point["mean_cost_per_attempted_task_usd"], point["mean_reward"]
        dominated = any(
            other["mean_cost_per_attempted_task_usd"] <= x
            and other["mean_reward"] >= y
            and (other["mean_cost_per_attempted_task_usd"] < x or other["mean_reward"] > y)
            for other in eligible
        )
        if not dominated:
            result.append(point["config_id"])
    return result


def render(data: dict, output: Path) -> dict:
    points, skipped = prepare_points(data)
    frontier_ids = frontier(points)
    split = data["metadata"]["split"]
    notes = []
    if any(p["cost_is_lower_bound"] for p in points):
        notes.append("Hollow markers with arrows show known-cost lower bounds, not exact costs.")
    if len({tuple(sorted(r["scored_task_ids"])) for r in data["summary"] if r["n_scored_tasks"]}) > 1:
        notes.append("Scored task sets differ; observed reward means are not directly comparable.")
    if not frontier_ids:
        notes.append("No frontier asserted: fewer than two configurations have full coverage and exact costs.")
    else:
        notes.append("Frontier is restricted to eligible configurations; incomplete observations are excluded.")
    if split == "dev":
        notes.append("DEV pipeline validation only; not final evaluation evidence.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter

    fig, ax = plt.subplots(figsize=(10, 6.5))
    colors = plt.get_cmap("tab10")
    max_cost = max(p["mean_cost_per_attempted_task_usd"] for p in points)
    xmax = max(max_cost * 1.45, 0.000001)
    ax.set_xlim(0, xmax)
    ax.set_ylim(-0.03, 1.08)
    ax.grid(True, alpha=0.22)
    ax.set_axisbelow(True)
    for i, point in enumerate(points):
        x, y = point["mean_cost_per_attempted_task_usd"], point["mean_reward"]
        color = colors(i % 10)
        ax.scatter([x], [y], s=90, facecolors=color if point["frontier_eligible"] else "white",
                   edgecolors=[color], linewidths=1.8, zorder=3)
        if point["cost_is_lower_bound"]:
            ax.annotate("", xy=(min(x + xmax * 0.075, xmax * 0.98), y), xytext=(x, y),
                        arrowprops={"arrowstyle": "->", "color": color, "lw": 1.6})
        label = f"{point['config_id']} ({point['n_scored_tasks']}/{point['n_expected_tasks']} scored)"
        ax.annotate(label, (x, y), xytext=(9, 12 if i % 2 == 0 else -20),
                    textcoords="offset points", fontsize=9, color=color)
    if frontier_ids:
        coordinates = sorted({(p["mean_cost_per_attempted_task_usd"], p["mean_reward"])
                              for p in points if p["config_id"] in frontier_ids})
        ax.plot([v[0] for v in coordinates], [v[1] for v in coordinates],
                color="#1b7f4b", linestyle="--", linewidth=1.5, zorder=2)
    ax.set_xlabel("Agent table cost per attempted task (USD; arrows indicate lower bounds)")
    ax.set_ylabel("Mean verifier reward on scored tasks")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, position: f"${value:.6f}"))
    ax.set_title(f"{split.upper()} — observed reward and agent cost", loc="left", fontsize=15, pad=14)
    handles = [Line2D([0], [0], marker="o", linestyle="none", markerfacecolor="white",
                      markeredgecolor="#444444", label="Partial coverage or incomplete cost")]
    if any(p["frontier_eligible"] for p in points):
        handles.append(Line2D([0], [0], marker="o", linestyle="none", color="#444444",
                              label="Full task coverage and exact cost"))
    if frontier_ids:
        handles.append(Line2D([0], [0], color="#1b7f4b", linestyle="--",
                              label="Pareto frontier among eligible configurations"))
    ax.legend(handles=handles, loc="upper right", fontsize=8)
    fig.text(0.08, 0.035, "\n".join(notes), fontsize=8, va="bottom", color="#444444")
    fig.subplots_adjust(left=0.09, right=0.96, bottom=0.24, top=0.88)
    stem = output.with_suffix("") if output.suffix.lower() in {".png", ".svg", ".json"} else output
    stem.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".png", ".svg"):
        fig.savefig(stem.with_suffix(suffix), dpi=180, facecolor="white")
    plt.close(fig)
    manifest = {"split": split, "points": points, "skipped": skipped,
                "frontier_config_ids": frontier_ids, "notes": notes,
                "cost_scope": "Agent inference only; see analysis.json for archived-attempt and verifier exclusions"}
    stem.with_suffix(".json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="analysis.json produced by analyze.py")
    parser.add_argument("--output", type=Path, required=True, help="Output filename stem (PNG, SVG and JSON)")
    args = parser.parse_args()
    try:
        result = render(json.loads(args.input.read_text()), args.output)
    except ImportError:
        parser.exit(1, "Plotting requires matplotlib. Install it with uv add matplotlib==3.10.8\n")
    except (ValueError, KeyError, OSError, TypeError) as error:
        parser.exit(1, f"Plotting failed: {error}\n")
    print(f"Plotted configurations: {len(result['points'])}")
    print("Frontier: " + (", ".join(result["frontier_config_ids"]) or "not asserted"))
    for note in result["notes"]:
        print(f"Note: {note}")
    print(f"Saved PNG, SVG and JSON using output stem: {args.output}")


if __name__ == "__main__":
    main()
