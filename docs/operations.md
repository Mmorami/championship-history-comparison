# Operations and Governance

## Refresh Cadence

- Historical backfill: one-off full run.
- Active season (`2025-26`): nightly refresh.
- Re-rank after every successful refresh.

## Run Versioning

- Every ranking execution writes a `scoring_runs` record with `run_id` and `scoring_version`.
- Snapshot results are immutable in `team_ranking_snapshot`.

## Monitoring

- Generate `quality_report.json` after every run.
- Generate `health_snapshot.json` for ingestion health and coverage drift.
- Alert when:
  - season count drops unexpectedly
  - promoted rows are missing for completed seasons
  - quality checks return warnings

## Data Quality Rules

- Core scoring includes only metrics with confidence `A/B`.
- `C/D` data appears in context endpoints only.
- Assists excluded from scoring unless `assists_coverage_complete_for_season = 1`.

## Auditability

- Raw source payloads are immutable and timestamped.
- `data_lineage` records source URLs, checksums, and quality grades.
