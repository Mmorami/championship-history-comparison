from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def validate_integrity(conn: sqlite3.Connection) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    checks = [
        (
            "w-d-l-played",
            """
            SELECT season_id, team_id FROM season_team_table
            WHERE wins + draws + losses != played
            LIMIT 100;
            """,
            "wins + draws + losses must equal played",
        ),
        (
            "gf-ga-gd",
            """
            SELECT season_id, team_id FROM season_team_table
            WHERE goals_for - goals_against != goal_diff
            LIMIT 100;
            """,
            "goals_for - goals_against must equal goal_diff",
        ),
        (
            "promotion-count",
            """
            SELECT season_id
            FROM season_team_table
            GROUP BY season_id
            HAVING SUM(promoted_auto) < 1 OR SUM(promoted_auto) > 2 OR SUM(promoted_playoff) > 1;
            """,
            "promotion counts outside expected range",
        ),
        (
            "legacy-1992-teamcount",
            """
            SELECT '1992-93' AS season_id
            WHERE
                (SELECT COUNT(*) FROM season_team_table WHERE season_id='1992-93') != 24
                OR (SELECT COUNT(DISTINCT position) FROM season_team_table WHERE season_id='1992-93') != 24
                OR (SELECT MIN(position) FROM season_team_table WHERE season_id='1992-93') != 1
                OR (SELECT MAX(position) FROM season_team_table WHERE season_id='1992-93') != 24;
            """,
            "1992-93 must have 24 teams with positions 1..24",
        ),
    ]

    for code, sql, message in checks:
        rows = conn.execute(sql).fetchall()
        for row in rows:
            findings.append({"check": code, "message": message, "season_id": row["season_id"]})

    return findings


def publish_quality_report(conn: sqlite3.Connection, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    findings = validate_integrity(conn)
    failed = len(findings) > 0
    summary = {
        "status": "fail" if failed else "pass",
        "thresholds": {
            "max_integrity_findings": 0,
        },
        "findings_count": len(findings),
        "findings": findings,
    }
    out = reports_dir / "quality_report.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out

