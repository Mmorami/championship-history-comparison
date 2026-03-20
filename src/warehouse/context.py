from __future__ import annotations

import re
import sqlite3

from warehouse.canonicalize import team_id_from_name, normalize_team_name


def player_id_from_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"player:{slug}"


def load_manager_record(
    conn: sqlite3.Connection,
    season_id: str,
    team_name: str,
    manager_name: str,
    from_date: str | None,
    to_date: str | None,
    is_primary_manager: bool,
    source_confidence: str = "B",
) -> None:
    team_id = team_id_from_name(normalize_team_name(team_name))
    conn.execute(
        """
        INSERT OR REPLACE INTO managers_by_season(
            season_id, team_id, manager_name, from_date, to_date, is_primary_manager, source_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (season_id, team_id, manager_name, from_date, to_date, int(is_primary_manager), source_confidence),
    )
    conn.commit()


def load_player_stat(
    conn: sqlite3.Connection,
    season_id: str,
    team_name: str,
    player_name: str,
    appearances: int | None,
    goals: int | None,
    assists: int | None,
    is_team_top_scorer: bool,
    source_confidence: str = "B",
    assists_coverage_complete_for_season: bool = False,
) -> None:
    team_id = team_id_from_name(normalize_team_name(team_name))
    player_id = player_id_from_name(player_name)
    conn.execute(
        "INSERT OR IGNORE INTO players(player_id, player_name) VALUES (?, ?);",
        (player_id, player_name),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO player_season_team_stats(
            season_id, team_id, player_id, appearances, goals, assists,
            is_team_top_scorer, source_confidence, assists_coverage_complete_for_season
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            season_id,
            team_id,
            player_id,
            appearances,
            goals,
            assists,
            int(is_team_top_scorer),
            source_confidence,
            int(assists_coverage_complete_for_season),
        ),
    )
    conn.commit()

