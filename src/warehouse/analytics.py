from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _load_scoring_weights(scoring_version: str) -> dict:
    config_path = Path("./scoring/versioned-configs") / f"{scoring_version}.json"
    if not config_path.exists():
        return {
            "performance": {"ppg": 0.5, "finish_percentile": 0.3, "gd_per_game": 0.2},
            "outcomes": {"auto": 0.7, "playoff": 0.3},
            "consistency": {"top6_total": 0.7, "playoff_conversion": 0.3},
            "overall": {"performance": 0.6, "outcomes": 0.25, "consistency": 0.15},
        }
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_views(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP VIEW IF EXISTS vw_promotion_candidates;
        CREATE VIEW vw_promotion_candidates AS
        SELECT *
        FROM season_team_table
        WHERE promoted_auto = 1 OR promoted_playoff = 1;

        DROP VIEW IF EXISTS vw_team_ranking_inputs;
        DROP VIEW IF EXISTS vw_season_team_ranking_inputs;
        CREATE VIEW vw_season_team_ranking_inputs AS
        SELECT
            s.season_id,
            s.team_id,
            s.position,
            s.played,
            s.points,
            s.ppg,
            s.goals_for,
            s.goals_against,
            s.goal_diff,
            s.finish_percentile,
            s.gd_per_game,
            s.promoted_auto,
            s.promoted_playoff,
            s.top6_flag
        FROM season_team_table s
        WHERE s.quality_grade IN ('A', 'B')
          AND (s.promoted_auto = 1 OR s.promoted_playoff = 1 OR s.top6_flag = 1);
        """
    )
    conn.commit()


def run_ranking_snapshot(conn: sqlite3.Connection, scoring_version: str) -> str:
    w = _load_scoring_weights(scoring_version)
    run_id = f"run:{uuid.uuid4()}"
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO scoring_runs(run_id, scoring_version, started_at_utc, status)
        VALUES (?, ?, ?, 'running');
        """,
        (run_id, scoring_version, now),
    )
    rows = conn.execute("SELECT * FROM vw_season_team_ranking_inputs;").fetchall()
    for row in rows:
        performance = (
            w["performance"]["ppg"] * row["ppg"] +
            w["performance"]["finish_percentile"] * row["finish_percentile"] +
            w["performance"]["gd_per_game"] * row["gd_per_game"]
        )
        # Outcomes for a single season: 1.0 for auto, 0.7 for playoff, else 0.
        outcomes = 1.0 if row["promoted_auto"] else 0.7 if row["promoted_playoff"] else 0.0
        
        # Consistency is less applicable here but we'll use top6_flag as a proxy.
        consistency = 1.0 if row["top6_flag"] else 0.0

        overall = (
            w["overall"]["performance"] * performance +
            w["overall"]["outcomes"] * outcomes +
            w["overall"]["consistency"] * consistency
        )
        conn.execute(
            """
            INSERT INTO team_ranking_snapshot(
                run_id, season_id, team_id, overall_score, performance_score, outcomes_score, consistency_score,
                position, played, points, ppg, goals_for, goals_against, goal_diff, finish_percentile,
                promoted_auto, promoted_playoff
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                run_id,
                row["season_id"],
                row["team_id"],
                overall,
                performance,
                outcomes,
                consistency,
                row["position"],
                row["played"],
                row["points"],
                row["ppg"],
                row["goals_for"],
                row["goals_against"],
                row["goal_diff"],
                row["finish_percentile"],
                row["promoted_auto"],
                row["promoted_playoff"],
            ),
        )
    conn.execute(
        "UPDATE scoring_runs SET status='completed', completed_at_utc=? WHERE run_id=?;",
        (datetime.now(timezone.utc).isoformat(), run_id),
    )
    conn.commit()
    return run_id


def write_api_payloads(conn: sqlite3.Connection, output_dir: Path, run_id: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    leaderboard = conn.execute(
        """
        SELECT t.team_name_canonical, s.*
        FROM team_ranking_snapshot s
        JOIN teams t ON t.team_id = s.team_id
        WHERE s.run_id = ?
        ORDER BY s.overall_score DESC;
        """,
        (run_id,),
    ).fetchall()

    leaderboard_payload = {
        "metadata": {
            "run_id": run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "rows": [dict(row) for row in leaderboard],
    }
    (output_dir / "leaderboard.json").write_text(
        json.dumps(leaderboard_payload, indent=2),
        encoding="utf-8",
    )

