"""Read-only configuration and integration check. Never calls a model."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

from harness.config import ROOT, load_config
from harness.prompts import render_templates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/harness/h0.yaml")
    args = parser.parse_args()
    config, stock = load_config(args.config)
    render_templates(stock, config)
    print(
        f"OK: {config.config_id}; model={stock['model']['model_name']}; components={config.components}"
    )
    load_dotenv(ROOT / ".env", override=False)
    print(
        "API key: "
        + (
            "present (not displayed)"
            if os.getenv("OPENROUTER_API_KEY")
            else "not set; offline tests still work"
        )
    )
    from harness.agent import factory

    try:
        factory(config.guardrail_factory)
        for plugin in config.plugins:
            factory(plugin)
    except RuntimeError as error:
        print(f"BLOCKED for live runs: {error}")
        return 2
    print("OK: integration factories import. Run unit tests and dev validation next.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
