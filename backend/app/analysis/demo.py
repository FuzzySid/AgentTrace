"""Run the paired comparisons and capture-tier matrix, then write a measured note."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.analysis.tax_harness import run_capture_matrix
from app.config.models import model_for_tier
from app.store.queries import confusion_matrix, cost_summary, regression_comparison, telemetry_tax

BACKEND = Path(__file__).resolve().parents[2]
TASKS = BACKEND / "fixtures" / "tasks.json"


def _run(run_id: str, *, tier: str, prompt_version: str) -> None:
    subprocess.run(
        [
            sys.executable, "-m", "app.run", "--tasks", str(TASKS), "--tier", tier,
            "--capture-tier", "attrs", "--prompt-version", prompt_version, "--run-id", run_id,
        ],
        cwd=BACKEND,
        check=True,
    )


def _write_tier_note(result: dict) -> Path:
    cheap = result["baseline"]
    mid = result["candidate"]
    cheaper_cost = result["cost_per_success_eur"]["baseline"]
    mid_cost = result["cost_per_success_eur"]["candidate"]
    if cheaper_cost > mid_cost:
        lead = f"On {result['paired_task_count']} paired fixtures, the cheap tier cost €{cheaper_cost:.6f} per successful session, more than mid at €{mid_cost:.6f}."
    else:
        lead = f"On {result['paired_task_count']} paired fixtures, cheap did not cost more per successful session: €{cheaper_cost:.6f} for cheap and €{mid_cost:.6f} for mid."
    body = [
        "# Paired tier comparison",
        "",
        lead,
        "",
        f"The failure rate was {result['failure_rate']['baseline']:.1%} for cheap and {result['failure_rate']['candidate']:.1%} for mid. P95 root-span latency was {result['p95_latency_ms']['baseline'] / 1000:.2f}s and {result['p95_latency_ms']['candidate'] / 1000:.2f}s, respectively.",
        "",
        f"The paired comparison found {len(result['newly_failing'])} newly failing tasks and {len(result['newly_fixed'])} newly fixed tasks. The fixture IDs were matched before rates, latency, or successful-session cost were computed.",
        "",
        "The open question is whether this difference persists across a broader task mix and repeated runs.",
        "",
    ]
    output = BACKEND.parent / "reports" / "tier-comparison.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(body), encoding="utf-8")
    return output


def main() -> None:
    # Validate both tiers before changing stored benchmark runs.
    model_for_tier("cheap")
    model_for_tier("mid")
    # One mid/verbose run also serves as the mid side of the tier comparison.
    _run("demo-prompt-verbose", tier="mid", prompt_version="verbose")
    _run("demo-prompt-terse", tier="mid", prompt_version="terse")
    _run("demo-tier-cheap", tier="cheap", prompt_version="verbose")
    run_capture_matrix(TASKS, "demo-tax", model_tier="mid", prompt_version="verbose")

    results = {
        "prompt_comparison": regression_comparison("prompt"),
        "tier_comparison": regression_comparison("tier"),
        "cost_summary": cost_summary("demo-prompt-verbose"),
        "confusion_matrix": confusion_matrix("demo-prompt-verbose"),
        "telemetry_tax": telemetry_tax("demo-tax-full"),
    }
    report = _write_tier_note(results["tier_comparison"])
    print(json.dumps({"summary": {"paired_tasks": results["tier_comparison"]["paired_task_count"], "cheap_cost_per_success": results["tier_comparison"]["cost_per_success_eur"]["baseline"], "mid_cost_per_success": results["tier_comparison"]["cost_per_success_eur"]["candidate"], "cost_sessions": results["cost_summary"]["session_count"], "eval_cost_eur": results["cost_summary"]["evaluation_cost_eur"], "matrix_accuracy": results["confusion_matrix"]["accuracy"], "full_bytes": results["telemetry_tax"]["tiers"][0]["total_bytes"]}, "report": str(report)}, indent=2))


if __name__ == "__main__":
    main()
