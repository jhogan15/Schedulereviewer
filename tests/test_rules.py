from schedulereviewer.models import Task
from schedulereviewer.rules import RuleConfig, review_schedule


def make_task(task_id: str, name: str, start: str, finish: str, duration: float, predecessors: str = "") -> Task:
    return Task.from_row(
        {
            "task_id": task_id,
            "name": name,
            "start_date": start,
            "finish_date": finish,
            "duration_days": str(duration),
            "location": "Zone B",
            "predecessors": predecessors,
        }
    )


def test_reviews_identify_multiple_issue_types() -> None:
    tasks = [
        make_task("1", "Procure steel", "2026-01-01", "2026-01-03", 3),
        make_task("2", "Erect steel frame", "2026-01-05", "2026-01-06", 1, "1"),
        make_task("3", "Main concrete pour", "2026-01-10", "2026-01-10", 1),
        make_task("4", "Podium concrete pour", "2026-01-10", "2026-01-10", 1),
    ]
    config = RuleConfig(
        max_major_pours_per_day=1,
        min_duration_by_keyword={"erect": 3},
        min_lead_time_days={"steel": 14},
    )

    findings = review_schedule(tasks, config)
    codes = {finding.code for finding in findings}

    assert "LOGIC_CONCRETE_OVERLAP" in codes
    assert "DURATION_UNREALISTIC" in codes
    assert "LEAD_TIME_TOO_SHORT" in codes
