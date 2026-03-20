from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Iterable

from warehouse.canonicalize import team_id_from_name, normalize_team_name
from warehouse.models import TeamSeasonRow


def upsert_season(
    conn: sqlite3.Connection,
    season_id: str,
    competition_name: str,
    teams_count: int,
    matches_per_team_planned: int,
    is_complete: bool,
) -> None:
    start_year = int(season_id.split("-")[0])
    end_suffix = season_id.split("-")[1]
    end_year = int(f"{str(start_year)[:2]}{end_suffix}")
    if end_year < start_year:
        end_year += 100
    conn.execute(
        """
        INSERT INTO seasons(
            season_id, competition_name, tier_level, start_year, end_year,
            teams_count, matches_per_team_planned, is_complete, data_cutoff_utc
        )
        VALUES (?, ?, 2, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(season_id) DO UPDATE SET
            competition_name=excluded.competition_name,
            teams_count=excluded.teams_count,
            matches_per_team_planned=excluded.matches_per_team_planned,
            is_complete=excluded.is_complete,
            data_cutoff_utc=excluded.data_cutoff_utc;
        """,
        (
            season_id,
            competition_name,
            start_year,
            end_year,
            teams_count,
            matches_per_team_planned,
            int(is_complete),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def _upsert_team(conn: sqlite3.Connection, team_name: str) -> str:
    canonical = normalize_team_name(team_name)
    team_id = team_id_from_name(canonical)
    conn.execute(
        """
        INSERT INTO teams(team_id, team_name_canonical) VALUES (?, ?)
        ON CONFLICT(team_id) DO UPDATE SET team_name_canonical=excluded.team_name_canonical;
        """,
        (team_id, canonical),
    )
    conn.execute(
        "INSERT OR IGNORE INTO team_aliases(alias_name, team_id) VALUES (?, ?);",
        (team_name, team_id),
    )
    return team_id


def load_season_team_rows(conn: sqlite3.Connection, rows: Iterable[TeamSeasonRow], season_teams_count: int) -> None:
    rows = list(rows)
    if not rows:
        return
    season_id = rows[0].season_id
    upsert_season(
        conn=conn,
        season_id=season_id,
        competition_name="English 2nd Tier",
        teams_count=season_teams_count,
        matches_per_team_planned=(season_teams_count - 1) * 2,
        is_complete=(season_id != "2025-26"),
    )
    for row in rows:
        team_id = _upsert_team(conn, row.team_name)
        goal_diff = row.goals_for - row.goals_against
        ppg = row.points / row.played if row.played else 0.0
        gd_per_game = goal_diff / row.played if row.played else 0.0
        finish_percentile = 1.0 - ((row.position - 1) / (season_teams_count - 1)) if season_teams_count > 1 else 1.0
        promotion_status = "auto" if row.promoted_auto else "playoff" if row.promoted_playoff else "none"
        conn.execute(
            """
            INSERT INTO season_team_table(
                season_id, team_id, position, played, wins, draws, losses,
                goals_for, goals_against, goal_diff, points, ppg, gd_per_game, finish_percentile,
                promoted_auto, promoted_playoff, playoff_participant, relegated,
                promotion_status, top6_flag, quality_grade
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(season_id, team_id) DO UPDATE SET
                position=excluded.position,
                played=excluded.played,
                wins=excluded.wins,
                draws=excluded.draws,
                losses=excluded.losses,
                goals_for=excluded.goals_for,
                goals_against=excluded.goals_against,
                goal_diff=excluded.goal_diff,
                points=excluded.points,
                ppg=excluded.ppg,
                gd_per_game=excluded.gd_per_game,
                finish_percentile=excluded.finish_percentile,
                promoted_auto=excluded.promoted_auto,
                promoted_playoff=excluded.promoted_playoff,
                playoff_participant=excluded.playoff_participant,
                relegated=excluded.relegated,
                promotion_status=excluded.promotion_status,
                top6_flag=excluded.top6_flag,
                quality_grade=excluded.quality_grade;
            """,
            (
                row.season_id,
                team_id,
                row.position,
                row.played,
                row.wins,
                row.draws,
                row.losses,
                row.goals_for,
                row.goals_against,
                goal_diff,
                row.points,
                ppg,
                gd_per_game,
                finish_percentile,
                int(row.promoted_auto),
                int(row.promoted_playoff),
                int(row.playoff_participant),
                int(row.relegated),
                promotion_status,
                int(row.position <= 6),
                row.quality_grade,
            ),
        )
    conn.commit()


def load_lineage(conn: sqlite3.Connection, entity_type: str, entity_key: str, source_name: str, source_url: str, quality_grade: str, checksum_raw: str | None = None, notes: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO data_lineage(entity_type, entity_key, source_name, source_url, fetched_at_utc, checksum_raw, quality_grade, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (entity_type, entity_key, source_name, source_url, datetime.now(timezone.utc).isoformat(), checksum_raw, quality_grade, notes),
    )
    conn.commit()


def load_playoff_result(
    conn: sqlite3.Connection,
    season_id: str,
    team_name: str,
    stage: str,
    quality_grade: str = "B",
) -> None:
    team_id = _upsert_team(conn, team_name)
    conn.execute(
        """
        INSERT INTO playoffs(
            season_id, team_id, playoff_stage_reached, playoff_matches, playoff_wins, playoff_losses, quality_grade
        ) VALUES (?, ?, ?, NULL, NULL, NULL, ?)
        ON CONFLICT(season_id, team_id) DO UPDATE SET
            playoff_stage_reached=excluded.playoff_stage_reached,
            quality_grade=excluded.quality_grade;
        """,
        (season_id, team_id, stage, quality_grade),
    )
    conn.commit()

