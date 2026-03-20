from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def write_health_snapshot(conn: sqlite3.Connection, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    seasons_count = conn.execute("SELECT COUNT(*) AS c FROM seasons;").fetchone()["c"]
    candidate_count = conn.execute(
        "SELECT COUNT(*) AS c FROM season_team_table WHERE promoted_auto=1 OR promoted_playoff=1;"
    ).fetchone()["c"]
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seasons_count": seasons_count,
        "promotion_candidate_rows": candidate_count,
    }
    target = output_dir / "health_snapshot.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target

