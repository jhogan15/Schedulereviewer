# Schedulereviewer

Schedulereviewer is an MVP for analyzing project schedules exported from Microsoft Project or Primavera P6 and highlighting risk signals.

## What it checks today

- **Logic conflicts**: flags multiple concrete pours in the same location on the same day.
- **Duration realism**: flags tasks with durations below configurable minimums for key task types.
- **Lead-time constraints**: flags tasks that begin too soon after predecessors when material/equipment lead-time rules apply.

## Why normalized CSV?

Native `.mpp` and `.xer` parsing can be added later, but a normalized CSV export gets value quickly and keeps the rules engine independent of source system.

Expected CSV columns:

- `task_id`
- `name`
- `start_date` (`YYYY-MM-DD`)
- `finish_date` (`YYYY-MM-DD`)
- `duration_days`
- `resource` (optional)
- `discipline` (optional)
- `location` (optional)
- `predecessors` (optional, semicolon-separated IDs)

## Quick start

```bash
python -m pip install -e .[dev]
pytest
schedulereviewer examples/sample_schedule.csv --config examples/rules.json
```

Example output:

```text
[HIGH] LOGIC_CONCRETE_OVERLAP tasks=B200, B210 :: 2 concrete pours are scheduled on 2026-04-12 at zone b; limit is 1.
[HIGH] LEAD_TIME_TOO_SHORT tasks=A110 :: Task 'Erect steel framing' has only 3 days from predecessor finish to start; requires at least 14 days for 'steel'.
[MEDIUM] LEAD_TIME_MISSING_PREDECESSOR tasks=C300 :: Task 'Switchgear installation' requires lead-time rule 'switchgear' but has no valid predecessor to measure from.
[MEDIUM] DURATION_UNREALISTIC tasks=A110 :: Task 'Erect steel framing' has duration 2.0 days, below configured minimum of 3.0 for keyword 'erect'.
[MEDIUM] DURATION_UNREALISTIC tasks=C300 :: Task 'Switchgear installation' has duration 2.0 days, below configured minimum of 4.0 for keyword 'installation'.
```

## Run in the browser

If you want a no-install UI, use the built-in browser app:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/web/` and either:

- upload your normalized CSV export, or
- paste CSV directly and click **Analyze Schedule**.

The browser UI uses the same core rule logic categories (concrete overlap, duration realism, lead-time checks) and supports custom JSON config overrides.

## Product roadmap (recommended)

1. **Import adapters**
   - Primavera XER/XML parser
   - MSP XML parser
   - Field mapping UI for custom enterprise schemas
2. **Rule packs**
   - Construction default rules (civil, structural, MEP)
   - Industry packs (data centers, infrastructure, oil & gas)
3. **Risk scoring**
   - Weight findings by critical path membership, float, and value-at-risk
4. **UX and reporting**
   - Web app with findings table, timeline overlays, and PDF summary output
5. **AI-assisted suggestions**
   - Explain likely causes and recommended corrective actions for each finding

## Architecture sketch

- `schedulereviewer/models.py`: task + finding models
- `schedulereviewer/rules.py`: deterministic rule checks
- `schedulereviewer/cli.py`: command-line entry point
- Future: API service + UI on top of this engine
