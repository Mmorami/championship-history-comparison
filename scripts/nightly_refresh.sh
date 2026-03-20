#!/usr/bin/env sh
set -eu

python -m warehouse.cli migrate
python -m warehouse.cli backfill --start-season 1992-93 --end-season 2025-26 --use-network
python -m warehouse.cli load-context
python -m warehouse.cli build-views
python -m warehouse.cli quality-report
python -m warehouse.cli reconcile-report --start-season 1992-93 --end-season 2025-26
python -m warehouse.cli health-snapshot
