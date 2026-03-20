# Championship History Warehouse

This project implements a reproducible data warehouse for the English second tier
from season `1992-93` to `2025-26` (current unfinished season).

## What it contains

- SQL migrations for warehouse schema.
- Ingestion connectors for historical web sources.
- Canonicalization and ID resolution.
- Backfill and incremental ETL jobs.
- Data quality checks and quality reports.
- Analytical views and API-ready JSON builders.
- Operations scripts for scheduled refresh and run versioning.

## Deployment

This project is designed for **zero-conversion free deployment** on platforms like Render or Railway.

### Strategy: Bundled SQLite
Because the database is small (~500KB), it is included in the Git repository. This allows you to deploy to "stateless" free tiers (like Render Free) without needing a separate database server or persistent volumes.

### Deploy to Render
1. Push your code to GitHub.
2. Sign in to [Render](https://render.com).
3. Click **New +** -> **Blueprint**.
4. Select this repository. Render will automatically detect the `render.yaml` and set up the service.

### Deploy to Railway
1. Push your code to GitHub.
2. Connect your repo to [Railway](https://railway.app).
3. Set the **Start Command** to `python -m warehouse serve`.
4. Railway will automatically inject the `PORT` variable.

## Quick start

1. Create a Python 3.11+ environment.
2. Install dependencies:
   - `pip install -e .`
   - Copy `.env.example` to `.env` and set values as needed.
3. Configure runtime environment variables:
   - `WAREHOUSE_DB_PATH` (default: `./data/warehouse.db`)
   - `RAW_DATA_DIR` (default: `./data/raw`)
   - `REPORTS_DIR` (default: `./data/reports`)
4. Run migrations:
   - `python -m warehouse.cli migrate`
5. Run historical backfill:
   - `python -m warehouse.cli backfill --start-season 1992-93 --end-season 2025-26 --use-network`
   - Add `--use-network` to enable live source fetching.
   - Without `--use-network`, deterministic fallback rows are loaded to keep the pipeline runnable.
   - For pilot validation: `python -m warehouse.cli pilot-ingestion --use-network`
6. Build analytical views and artifacts:
   - `python -m warehouse.cli build-views`
7. Produce quality report:
   - `python -m warehouse.cli quality-report`
8. Produce reconciliation and coverage reports:
   - `python -m warehouse.cli reconcile-report --start-season 1992-93 --end-season 2025-26`
9. Start API + UI:
   - `python -m warehouse.cli serve --host 127.0.0.1 --port 8080`

## Notes

- Core scoring uses only high-confidence team-season metrics.
- Manager and player data are tagged with confidence grades and kept context-first.
- Assists are ingested but excluded from scoring unless season-level coverage is complete.
- Default primary source is football-data CSV for real historical backfill.
