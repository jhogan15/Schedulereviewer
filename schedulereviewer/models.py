from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(slots=True)
class Task:
    task_id: str
    name: str
    start_date: date
    finish_date: date
    duration_days: float
    resource: str = ""
    discipline: str = ""
    location: str = ""
    predecessors: tuple[str, ...] = ()

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Task":
        task_id = row.get("task_id", "").strip()
        name = row.get("name", "").strip()
        start_date = parse_date(row.get("start_date", ""))
        finish_date = parse_date(row.get("finish_date", ""))

        duration_raw = row.get("duration_days", "0").strip() or "0"
        duration_days = float(duration_raw)

        predecessors = tuple(
            item.strip()
            for item in row.get("predecessors", "").split(";")
            if item.strip()
        )

        return cls(
            task_id=task_id,
            name=name,
            start_date=start_date,
            finish_date=finish_date,
            duration_days=duration_days,
            resource=row.get("resource", "").strip(),
            discipline=row.get("discipline", "").strip(),
            location=row.get("location", "").strip(),
            predecessors=predecessors,
        )


@dataclass(slots=True)
class Finding:
    code: str
    severity: str
    message: str
    task_ids: tuple[str, ...] = ()


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()
