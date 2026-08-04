# Nightly Telemetry Export

`nightly_export.py` is an independent worker. It creates or claims a
`public.job_runs` row, exports the previous UTC calendar day's
`telemetry_events` to `data/raw/telemetry_YYYY-MM-DD.csv` when the snapshot is
missing, and launches `data/pipelines/pipeline.py` as a child process. The CSV
is an audit backup; the pipeline continues to read telemetry from the
database.

## Manual run

From the repository root, with the `services/api` environment available:

```sh
python scripts/nightly_export.py
```

For a deterministic test date:

```sh
TARGET_DATE=2026-07-14 python scripts/nightly_export.py
```

## Scheduling

Install [`crontab.example`](./crontab.example) on the worker host. It uses
`0 2 * * *` in UTC and does not run inside the FastAPI process. The
`processing` row status is the only lock, so a second overlapping invocation
exits with a logged `skipped` result.
