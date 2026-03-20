from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from warehouse.pipeline import season_range


def write_backfill_coverage(conn: sqlite3.Connection, reports_dir: Path, start_season: str, end_season: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    seasons = season_range(start_season, end_season)
    rows = conn.execute(
        """
        SELECT season_id, COUNT(*) AS teams_loaded, MIN(quality_grade) AS min_grade, MAX(quality_grade) AS max_grade
        FROM season_team_table
        GROUP BY season_id
        ORDER BY season_id;
        """
    ).fetchall()
    by_season = {r["season_id"]: dict(r) for r in rows}
    payload = {
        "requested_seasons": seasons,
        "loaded_seasons": list(by_season.keys()),
        "missing_seasons": [s for s in seasons if s not in by_season],
        "coverage": [by_season[s] for s in seasons if s in by_season],
    }
    out = reports_dir / "backfill_coverage.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def write_reconciliation_summary(conn: sqlite3.Connection, reports_dir: Path, start_season: str, end_season: str) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    seasons = season_range(start_season, end_season)
    lineage_rows = conn.execute(
        """
        SELECT entity_key AS season_id, source_name, COUNT(*) AS records
        FROM data_lineage
        WHERE entity_type IN (
            'season_table',
            'season_matches_csv',
            'legacy_standings',
            'playoff_winner_inferred'
        )
        GROUP BY entity_key, source_name
        ORDER BY entity_key, source_name;
        """
    ).fetchall()
    sources_by_season: dict[str, dict[str, int]] = {s: {} for s in seasons}
    for row in lineage_rows:
        sid = row["season_id"]
        if sid in sources_by_season:
            sources_by_season[sid][row["source_name"]] = row["records"]
    payload = {
        "seasons": seasons,
        "source_presence_by_season": sources_by_season,
        "notes": "Primary reconciliation tracks source presence and lineage completeness for each season.",
    }
    out = reports_dir / "reconciliation_summary.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out

