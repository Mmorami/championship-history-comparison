from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from html.parser import HTMLParser
import html as html_lib

from warehouse.models import TeamSeasonRow


def parse_season_table_html(season_id: str, html: str) -> list[TeamSeasonRow]:
    """
    Parse a generic league table HTML payload.
    This parser is intentionally defensive and expects source-specific wrappers
    to pre-select the standings table.
    """
    if "<table" not in html.lower():
        return []
    table_match = re.search(r"<table.*?</table>", html, flags=re.IGNORECASE | re.DOTALL)
    if not table_match:
        return []
    table_html = table_match.group(0)
    tr_matches = re.findall(r"<tr.*?</tr>", table_html, flags=re.IGNORECASE | re.DOTALL)
    rows: list[TeamSeasonRow] = []
    for tr in tr_matches:
        tds = re.findall(r"<td.*?>(.*?)</td>", tr, flags=re.IGNORECASE | re.DOTALL)
        tds = [re.sub(r"<[^>]+>", "", td).strip() for td in tds]
        if len(tds) < 10:
            continue
        if not re.match(r"^\d+$", tds[0]):
            continue
        try:
            position = int(tds[0])
            team_name = tds[1]
            played = int(tds[2])
            wins = int(tds[3])
            draws = int(tds[4])
            losses = int(tds[5])
            goals_for = int(tds[6])
            goals_against = int(tds[7])
            points = int(tds[9])
        except ValueError:
            continue
        rows.append(
            TeamSeasonRow(
                season_id=season_id,
                team_name=team_name,
                position=position,
                played=played,
                wins=wins,
                draws=draws,
                losses=losses,
                goals_for=goals_for,
                goals_against=goals_against,
                points=points,
                promoted_auto=False,
                promoted_playoff=False,
                playoff_participant=False,
                relegated=False,
            )
        )
    # Re-calculate relegation based on final count (bottom 3)
    total = len(rows)
    for row in rows:
        if row.position > (total - 3):
            row.relegated = True
    return rows


def parse_football_data_csv_to_table(season_id: str, csv_text: str) -> list[TeamSeasonRow]:
    """
    Build a final table from match-level CSV rows (football-data.co.uk format).
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
    )

    for row in reader:
        home = (row.get("HomeTeam") or "").strip()
        away = (row.get("AwayTeam") or "").strip()
        fthg = row.get("FTHG")
        ftag = row.get("FTAG")
        ftr = (row.get("FTR") or "").strip().upper()
        if not home or not away:
            continue
        if fthg in (None, "") or ftag in (None, ""):
            continue
        try:
            home_goals = int(float(fthg))
            away_goals = int(float(ftag))
        except ValueError:
            continue

        stats[home]["played"] += 1
        stats[away]["played"] += 1
        stats[home]["goals_for"] += home_goals
        stats[home]["goals_against"] += away_goals
        stats[away]["goals_for"] += away_goals
        stats[away]["goals_against"] += home_goals

        if ftr == "H":
            stats[home]["wins"] += 1
            stats[away]["losses"] += 1
            stats[home]["points"] += 3
        elif ftr == "A":
            stats[away]["wins"] += 1
            stats[home]["losses"] += 1
            stats[away]["points"] += 3
        else:
            stats[home]["draws"] += 1
            stats[away]["draws"] += 1
            stats[home]["points"] += 1
            stats[away]["points"] += 1

    ranked = sorted(
        stats.items(),
        key=lambda kv: (
            kv[1]["points"],
            kv[1]["goals_for"] - kv[1]["goals_against"],
            kv[1]["goals_for"],
            kv[0],
        ),
        reverse=True,
    )

    rows: list[TeamSeasonRow] = []
    for i, (team, s) in enumerate(ranked, start=1):
        rows.append(
            TeamSeasonRow(
                season_id=season_id,
                team_name=team,
                position=i,
                played=s["played"],
                wins=s["wins"],
                draws=s["draws"],
                losses=s["losses"],
                goals_for=s["goals_for"],
                goals_against=s["goals_against"],
                points=s["points"],
                promoted_auto=(i <= 2),
                promoted_playoff=(i == 3),
                playoff_participant=(i in (3, 4, 5, 6)),
                relegated=(i > (len(ranked) - 3)),
                quality_grade="A",
            )
        )
    return rows


def parse_wikipedia_standings_html(season_id: str, html: str, section_marker: str | None = None) -> list[TeamSeasonRow]:
    """
    Parse a Wikipedia standings wikitable for legacy seasons.
    If section_marker is provided, it looks for the first wikitable after that text.
    """
    if section_marker:
        # Locate the marker and slice the HTML to search only after it.
        # This is useful when one page contains tables for multiple divisions (e.g. 1991-92).
        idx = html.find(section_marker)
        if idx != -1:
            html = html[idx:]

    tables = re.findall(
        r"<table[^>]*class=\"[^\"]*wikitable[^\"]*\"[^>]*>.*?</table>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    table_html = None
    for t in tables:
        # Search for headers inside this table block.
        if re.search(r"\bPld\b", t, flags=re.IGNORECASE) and re.search(r"\bPts\b", t, flags=re.IGNORECASE):
            table_html = t
            break
    if not table_html:
        return []

    class _TableParser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.in_tr = False
            self.in_cell = False
            self.current_row: list[str] = []
            self.cell_chunks: list[str] = []
            self.rows: list[list[str]] = []

        def handle_starttag(self, tag: str, attrs) -> None:
            tag = tag.lower()
            if tag == "tr":
                self.in_tr = True
                self.current_row = []
            elif self.in_tr and tag in ("td", "th"):
                self.in_cell = True
                self.cell_chunks = []

        def handle_data(self, data: str) -> None:
            if self.in_cell:
                self.cell_chunks.append(data)

        def handle_endtag(self, tag: str) -> None:
            tag = tag.lower()
            if self.in_cell and tag in ("td", "th"):
                self.in_cell = False
                text = html_lib.unescape("".join(self.cell_chunks))
                text = re.sub(r"\s+", " ", text).strip()
                self.current_row.append(text)
            elif tag == "tr" and self.in_tr:
                self.in_tr = False
                if self.current_row:
                    self.rows.append(self.current_row)

    def _norm_header(s: str) -> str:
        s = html_lib.unescape(s)
        s = re.sub(r"\s+", "", s.strip().lower())
        s = re.sub(r"[^a-z0-9]", "", s)
        return s

    def _extract_int(s: str) -> int | None:
        s = html_lib.unescape(s)
        s = s.replace("−", "-")
        m = re.search(r"-?\d+", s)
        if not m:
            return None
        try:
            return int(m.group(0))
        except ValueError:
            return None

    def _clean_team_name(team_cell: str) -> str:
        team_cell = re.sub(r"\[\d+\]", "", team_cell).strip()
        # Remove Wikipedia promotion/relegation markers like "(C, P)", "(O, P)", "(R)".
        team_cell = re.sub(r"\s*\(([A-Za-z.,\s]+)\)\s*$", "", team_cell).strip()
        return team_cell

    parser = _TableParser()
    parser.feed(table_html)
    if not parser.rows:
        return []

    header = parser.rows[0]
    headers_norm = [_norm_header(c) for c in header]

    # Build indices by header names.
    # Expected: Pos, Team, Pld, W, D, L, GF, GA, GD, Pts, [Notes...]
    idx_pos = headers_norm.index("pos") if "pos" in headers_norm else 0
    idx_team = headers_norm.index("team") if "team" in headers_norm else 1
    idx_pld = headers_norm.index("pld") if "pld" in headers_norm else 2
    idx_w = headers_norm.index("w") if "w" in headers_norm else 3
    idx_d = headers_norm.index("d") if "d" in headers_norm else 4
    idx_l = headers_norm.index("l") if "l" in headers_norm else 5
    idx_gf = headers_norm.index("gf") if "gf" in headers_norm else 6
    idx_ga = headers_norm.index("ga") if "ga" in headers_norm else 7
    idx_pts = headers_norm.index("pts") if "pts" in headers_norm else 9

    parsed_rows: list[TeamSeasonRow] = []
    for row in parser.rows[1:]:
        if len(row) <= max(idx_pts, idx_ga, idx_gf, idx_pld):
            # Not enough columns to trust the parse.
            continue

        pos = _extract_int(row[idx_pos])
        played = _extract_int(row[idx_pld])
        wins = _extract_int(row[idx_w])
        draws = _extract_int(row[idx_d])
        losses = _extract_int(row[idx_l])
        gf = _extract_int(row[idx_gf])
        ga = _extract_int(row[idx_ga])
        points = _extract_int(row[idx_pts])

        if None in (pos, played, wins, draws, losses, gf, ga, points):
            continue

        team = _clean_team_name(row[idx_team])
        if not team:
            continue

        parsed_rows.append(
            TeamSeasonRow(
                season_id=season_id,
                team_name=team,
                position=int(pos),
                played=int(played),
                wins=int(wins),
                draws=int(draws),
                losses=int(losses),
                goals_for=int(gf),
                goals_against=int(ga),
                points=int(points),
                promoted_auto=(pos <= 2),
                promoted_playoff=(pos == 3),
                playoff_participant=(pos in (3, 4, 5, 6)),
                relegated=(pos > (len(parser.rows) - 4)),
                quality_grade="B",
            )
        )

    # Prefer tables that produce a full set of 24 teams.
    if len(parsed_rows) >= 24:
        return parsed_rows
    return parsed_rows

