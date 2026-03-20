from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from warehouse.canonicalize import normalize_team_name
from warehouse.connectors import SOURCES, fetch_url, store_raw_payload
from warehouse.loaders import load_lineage, load_playoff_result, load_season_team_rows
from warehouse.models import TeamSeasonRow
from warehouse.parsers import parse_football_data_csv_to_table, parse_season_table_html, parse_wikipedia_standings_html


_OVERRIDES_PATH = Path(__file__).resolve().parents[2] / "data" / "playoff_overrides.json"


def _load_playoff_overrides() -> dict[str, str | None]:
    """Return mapping of season_id -> canonical winner team name (or None if unknown)."""
    if not _OVERRIDES_PATH.exists():
        return {}
    return json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))


def _apply_playoff_overrides(
    rows: list[TeamSeasonRow], season_id: str, overrides: dict[str, str | None]
) -> list[TeamSeasonRow]:
    """
    Correct promoted_playoff flags using verified override data.

    If the season has a known playoff winner:
    - Clear promoted_playoff on all rows
    - Set promoted_playoff=True only on the matching team
    - Ensure playoff_participant is set for positions 3–6
    If the season has no override entry (or value is null), rows are returned unchanged.
    """
    winner_name = overrides.get(season_id)  # None if missing key or explicit null
    if not winner_name:
        return rows
    winner_canonical = normalize_team_name(winner_name)
    corrected: list[TeamSeasonRow] = []
    winner_found = False
    for row in rows:
        row_canonical = normalize_team_name(row.team_name)
        is_winner = row_canonical == winner_canonical
        if is_winner:
            winner_found = True
        corrected.append(
            TeamSeasonRow(
                season_id=row.season_id,
                team_name=row.team_name,
                position=row.position,
                played=row.played,
                wins=row.wins,
                draws=row.draws,
                losses=row.losses,
                goals_for=row.goals_for,
                goals_against=row.goals_against,
                points=row.points,
                promoted_auto=row.promoted_auto,
                promoted_playoff=is_winner and not row.promoted_auto,
                playoff_participant=row.position in (3, 4, 5, 6),
                relegated=row.relegated,
                quality_grade=row.quality_grade,
            )
        )
    if not winner_found:
        # Override name didn't match any parsed team — log and return original rows unchanged.
        print(
            f"[playoff_overrides] WARNING: override winner '{winner_name}' "
            f"(canonical: '{winner_canonical}') not found in parsed rows for {season_id}. "
            "Skipping override — positional inference will be used."
        )
        return rows
    return corrected


def season_range(start_season: str, end_season: str) -> list[str]:
    start = int(start_season.split("-")[0])
    end = int(end_season.split("-")[0])
    out: list[str] = []
    for year in range(start, end + 1):
        out.append(f"{year}-{str(year + 1)[-2:]}")
    return out


def _fallback_stub_rows(season_id: str) -> list[TeamSeasonRow]:
    # Deterministic stub keeps the pipeline runnable before source-specific parsers are finalized.
    teams = [
        ("Leicester City", 1, True, False),
        ("Ipswich Town", 2, True, False),
        ("Leeds United", 3, False, True),
        ("Southampton", 4, False, False),
        ("West Bromwich Albion", 5, False, False),
        ("Norwich City", 6, False, False),
    ]
    rows: list[TeamSeasonRow] = []
    for i, (name, pos, auto, playoff) in enumerate(teams, start=1):
        rows.append(
            TeamSeasonRow(
                season_id=season_id,
                team_name=name,
                position=pos,
                played=46,
                wins=max(15, 28 - i),
                draws=10,
                losses=max(2, 46 - (max(15, 28 - i) + 10)),
                goals_for=max(40, 78 - i * 2),
                goals_against=30 + i,
                points=max(60, 100 - i * 3),
                promoted_auto=auto,
                promoted_playoff=playoff,
                playoff_participant=(pos in (3, 4, 5, 6)),
                relegated=False,
                quality_grade="B",
            )
        )
    return rows


def _season_to_football_data_code(season_id: str) -> str | None:
    start_year = int(season_id.split("-")[0])
    # football-data.co.uk second-tier historical files are reliably available from 1993-94.
    if start_year < 1993:
        return None
    return f"{str(start_year)[-2:]}{str((start_year + 1) % 100).zfill(2)}"


def _football_data_url(season_id: str) -> str | None:
    code = _season_to_football_data_code(season_id)
    if code is None:
        return None
    return f"https://www.football-data.co.uk/mmz4281/{code}/E1.csv"


def backfill_core(
    conn: sqlite3.Connection,
    raw_data_dir: Path,
    start_season: str,
    end_season: str,
    use_network: bool = False,
) -> None:
    playoff_overrides = _load_playoff_overrides()
    for season_id in season_range(start_season, end_season):
        conn.execute("DELETE FROM data_lineage WHERE entity_key = ?;", (season_id,))
        conn.commit()
        collected_rows: list[TeamSeasonRow] = []
        if use_network:
            primary_url = _football_data_url(season_id)
            if primary_url:
                try:
                    csv_text = fetch_url(primary_url)
                    envelope = store_raw_payload(
                        raw_data_dir=raw_data_dir,
                        source_name="football_data",
                        entity="season_matches_csv",
                        season_id=season_id,
                        payload=csv_text,
                        source_url=primary_url,
                    )
                    load_lineage(
                        conn,
                        entity_type="season_matches_csv",
                        entity_key=season_id,
                        source_name="football_data",
                        source_url=primary_url,
                        quality_grade="A",
                        checksum_raw=envelope["checksum_raw"],
                    )
                    collected_rows = parse_football_data_csv_to_table(season_id=season_id, csv_text=csv_text)
                except Exception as exc:  # pragma: no cover - network/source failures expected
                    load_lineage(
                        conn,
                        entity_type="season_matches_csv",
                        entity_key=season_id,
                        source_name="football_data",
                        source_url=primary_url,
                        quality_grade="D",
                        notes=f"fetch_or_parse_error={exc}",
                    )
            elif season_id == "1991-92":
                wiki_url = "https://en.wikipedia.org/wiki/1991%E2%80%9392_Football_League_Second_Division"
                try:
                    html = fetch_url(wiki_url)
                    envelope = store_raw_payload(
                        raw_data_dir=raw_data_dir,
                        source_name="wikipedia",
                        entity="legacy_standings",
                        season_id=season_id,
                        payload=html,
                        source_url=wiki_url,
                    )
                    load_lineage(
                        conn,
                        entity_type="legacy_standings",
                        entity_key=season_id,
                        source_name="wikipedia",
                        source_url=wiki_url,
                        quality_grade="B",
                        checksum_raw=envelope["checksum_raw"],
                    )
                    collected_rows = parse_wikipedia_standings_html(
                        season_id=season_id, html=html, section_marker='id="Second_Division"'
                    )
                except Exception as exc:  # pragma: no cover
                    load_lineage(
                        conn,
                        entity_type="legacy_standings",
                        entity_key=season_id,
                        source_name="wikipedia",
                        source_url=wiki_url,
                        quality_grade="D",
                        notes=f"fetch_or_parse_error={exc}",
                    )
            elif season_id == "1992-93":
                wiki_url = "https://en.wikipedia.org/wiki/1992%E2%80%9393_Football_League_First_Division"
                try:
                    html = fetch_url(wiki_url)
                    envelope = store_raw_payload(
                        raw_data_dir=raw_data_dir,
                        source_name="wikipedia",
                        entity="legacy_standings",
                        season_id=season_id,
                        payload=html,
                        source_url=wiki_url,
                    )
                    load_lineage(
                        conn,
                        entity_type="legacy_standings",
                        entity_key=season_id,
                        source_name="wikipedia",
                        source_url=wiki_url,
                        quality_grade="B",
                        checksum_raw=envelope["checksum_raw"],
                    )
                    collected_rows = parse_wikipedia_standings_html(
                        season_id=season_id, html=html, section_marker='id="Table"'
                    )
                except Exception as exc:  # pragma: no cover
                    load_lineage(
                        conn,
                        entity_type="legacy_standings",
                        entity_key=season_id,
                        source_name="wikipedia",
                        source_url=wiki_url,
                        quality_grade="D",
                        notes=f"fetch_or_parse_error={exc}",
                    )
            for source in SOURCES:
                if collected_rows:
                    break
                source_url = f"{source.base_url}/"
                try:
                    html = fetch_url(source_url)
                except Exception as exc:  # pragma: no cover - network and source failures expected
                    load_lineage(
                        conn,
                        entity_type="season_table",
                        entity_key=season_id,
                        source_name=source.name,
                        source_url=source_url,
                        quality_grade="D",
                        notes=f"fetch_error={exc}",
                    )
                    continue
                envelope = store_raw_payload(
                    raw_data_dir=raw_data_dir,
                    source_name=source.name,
                    entity="season_table",
                    season_id=season_id,
                    payload=html,
                    source_url=source_url,
                )
                load_lineage(
                    conn,
                    entity_type="season_table",
                    entity_key=season_id,
                    source_name=source.name,
                    source_url=source_url,
                    quality_grade="C",
                    checksum_raw=envelope["checksum_raw"],
                )
                parsed = parse_season_table_html(season_id=season_id, html=html)
                if parsed:
                    collected_rows = parsed
                    break
        if not collected_rows:
            collected_rows = _fallback_stub_rows(season_id)
            load_lineage(
                conn,
                entity_type="season_table",
                entity_key=season_id,
                source_name="fallback_stub",
                source_url="internal://stub",
                quality_grade="D",
                notes="Network parser disabled or no parseable source found.",
            )
        # Apply verified playoff winner overrides before persisting.
        collected_rows = _apply_playoff_overrides(collected_rows, season_id, playoff_overrides)
        conn.execute("DELETE FROM season_team_table WHERE season_id = ?;", (season_id,))
        conn.execute("DELETE FROM playoffs WHERE season_id = ?;", (season_id,))
        conn.commit()
        load_season_team_rows(conn, collected_rows, season_teams_count=len(collected_rows))
        for row in collected_rows:
            if row.position in (3, 4, 5, 6):
                stage = "winner" if row.promoted_playoff else "semi_final"
                load_playoff_result(conn, season_id=row.season_id, team_name=row.team_name, stage=stage, quality_grade="B")
        for row in collected_rows:
            if row.promoted_playoff:
                load_lineage(
                    conn,
                    entity_type="playoff_winner_inferred",
                    entity_key=f"{season_id}:{row.team_name}",
                    source_name="inference_from_final_table",
                    source_url="internal://table-inference",
                    quality_grade="B",
                    notes="Playoff winner inferred from final-table ranking position 3.",
                )

