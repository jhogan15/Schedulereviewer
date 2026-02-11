from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import Finding, Task


@dataclass(slots=True)
class RuleConfig:
    concrete_keywords: tuple[str, ...] = ("concrete", "pour")
    max_major_pours_per_day: int = 1
    min_duration_by_keyword: dict[str, float] | None = None
    min_lead_time_days: dict[str, int] | None = None


def review_schedule(tasks: list[Task], config: RuleConfig) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_overlapping_concrete_pours(tasks, config))
    findings.extend(check_unrealistic_durations(tasks, config))
    findings.extend(check_lead_time_constraints(tasks, config))
    return findings


def check_overlapping_concrete_pours(tasks: list[Task], config: RuleConfig) -> list[Finding]:
    by_day: dict[tuple, list[Task]] = defaultdict(list)
    key_terms = tuple(k.lower() for k in config.concrete_keywords)

    for task in tasks:
        lowered = task.name.lower()
        is_concrete = any(term in lowered for term in key_terms)
        if is_concrete:
            day_key = (task.start_date, task.location.lower())
            by_day[day_key].append(task)

    findings: list[Finding] = []
    for (day, location), day_tasks in by_day.items():
        if len(day_tasks) > config.max_major_pours_per_day:
            findings.append(
                Finding(
                    code="LOGIC_CONCRETE_OVERLAP",
                    severity="high",
                    message=(
                        f"{len(day_tasks)} concrete pours are scheduled on {day} at {location or 'unspecified location'}; "
                        f"limit is {config.max_major_pours_per_day}."
                    ),
                    task_ids=tuple(t.task_id for t in day_tasks),
                )
            )

    return findings


def check_unrealistic_durations(tasks: list[Task], config: RuleConfig) -> list[Finding]:
    thresholds = config.min_duration_by_keyword or {}
    findings: list[Finding] = []

    for task in tasks:
        lowered = task.name.lower()
        for keyword, minimum in thresholds.items():
            if keyword.lower() in lowered and task.duration_days < minimum:
                findings.append(
                    Finding(
                        code="DURATION_UNREALISTIC",
                        severity="medium",
                        message=(
                            f"Task '{task.name}' has duration {task.duration_days} days, "
                            f"below configured minimum of {minimum} for keyword '{keyword}'."
                        ),
                        task_ids=(task.task_id,),
                    )
                )

    return findings


def check_lead_time_constraints(tasks: list[Task], config: RuleConfig) -> list[Finding]:
    lead_rules = config.min_lead_time_days or {}
    if not lead_rules:
        return []

    task_by_id = {task.task_id: task for task in tasks}
    findings: list[Finding] = []

    for task in tasks:
        lowered_name = task.name.lower()
        for keyword, min_days in lead_rules.items():
            if keyword.lower() not in lowered_name:
                continue

            predecessor_finishes = [
                task_by_id[pid].finish_date
                for pid in task.predecessors
                if pid in task_by_id
            ]

            if not predecessor_finishes:
                findings.append(
                    Finding(
                        code="LEAD_TIME_MISSING_PREDECESSOR",
                        severity="medium",
                        message=(
                            f"Task '{task.name}' requires lead-time rule '{keyword}' but has no valid predecessor to measure from."
                        ),
                        task_ids=(task.task_id,),
                    )
                )
                continue

            latest_finish = max(predecessor_finishes)
            actual_gap = (task.start_date - latest_finish).days
            if actual_gap < min_days:
                findings.append(
                    Finding(
                        code="LEAD_TIME_TOO_SHORT",
                        severity="high",
                        message=(
                            f"Task '{task.name}' has only {actual_gap} days from predecessor finish to start; "
                            f"requires at least {min_days} days for '{keyword}'."
                        ),
                        task_ids=(task.task_id,),
                    )
                )

    return findings
