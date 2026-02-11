from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .models import Finding, Task
from .rules import RuleConfig, review_schedule


def load_tasks(path: Path) -> list[Task]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        return [Task.from_row(row) for row in rows]


def load_config(path: Path | None) -> RuleConfig:
    if path is None:
        return RuleConfig(
            min_duration_by_keyword={"concrete": 3, "commissioning": 5},
            min_lead_time_days={"steel": 14, "switchgear": 45},
        )

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    return RuleConfig(
        concrete_keywords=tuple(data.get("concrete_keywords", ["concrete", "pour"])),
        max_major_pours_per_day=int(data.get("max_major_pours_per_day", 1)),
        min_duration_by_keyword={
            k: float(v)
            for k, v in data.get("min_duration_by_keyword", {}).items()
        },
        min_lead_time_days={
            k: int(v)
            for k, v in data.get("min_lead_time_days", {}).items()
        },
    )


def print_findings(findings: list[Finding]) -> None:
    if not findings:
        print("No findings. Schedule passed configured checks.")
        return

    severity_order = {"high": 0, "medium": 1, "low": 2}
    ordered = sorted(findings, key=lambda f: severity_order.get(f.severity, 99))
    for finding in ordered:
        tasks = ", ".join(finding.task_ids) if finding.task_ids else "n/a"
        print(f"[{finding.severity.upper()}] {finding.code} tasks={tasks} :: {finding.message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review schedule exports for risk flags and logic errors")
    parser.add_argument("schedule_csv", type=Path, help="Path to normalized CSV export from MSP/P6")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional JSON file defining lead times, duration thresholds, and logic limits",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    tasks = load_tasks(args.schedule_csv)
    config = load_config(args.config)
    findings = review_schedule(tasks, config)
    print_findings(findings)


if __name__ == "__main__":
    main()
