from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import anthropic
import groq

from warehouse.config import get_settings

def _json_response(handler: BaseHTTPRequestHandler, payload: dict, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_text(path: Path) -> bytes:
    return path.read_text(encoding="utf-8").encode("utf-8")


class WarehouseApiHandler(BaseHTTPRequestHandler):
    db_path: Path
    web_root: Path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            content = _read_text(self.web_root / "index.html")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/app.js":
            content = _read_text(self.web_root / "app.js")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/column-studio":
            content = _read_text(self.web_root / "column-studio.html")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path in ("/column_studio.js", "/column_injector.js"):
            filename = path.lstrip("/")
            content = _read_text(self.web_root / filename)
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/styles.css":
            content = _read_text(self.web_root / "styles.css")
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        if path == "/api/seasons":
            with self._conn() as conn:
                rows = conn.execute(
                    """
                    SELECT season_id
                    FROM seasons
                    ORDER BY start_year ASC;
                    """
                ).fetchall()
            _json_response(self, {"metadata": {}, "rows": [r["season_id"] for r in rows]})
            return

        if path == "/api/leaderboard":
            with self._conn() as conn:
                run = conn.execute(
                    "SELECT run_id, completed_at_utc FROM scoring_runs WHERE status='completed' ORDER BY completed_at_utc DESC LIMIT 1;"
                ).fetchone()
                if run is None:
                    _json_response(self, {"metadata": {}, "rows": []})
                    return
                rows = conn.execute(
                    """
                    SELECT t.team_name_canonical, s.*
                    FROM team_ranking_snapshot s
                    JOIN teams t ON t.team_id = s.team_id
                    WHERE s.run_id = ? AND (s.promoted_auto = 1 OR s.promoted_playoff = 1)
                    ORDER BY s.overall_score DESC
                    LIMIT 100;
                    """,
                    (run["run_id"],),
                ).fetchall()
            _json_response(
                self,
                {
                    "metadata": {"run_id": run["run_id"], "data_cutoff_utc": run["completed_at_utc"]},
                    "rows": [dict(r) for r in rows],
                },
            )
            return

        if path.startswith("/api/team/") and path.endswith("/timeline"):
            team_id = path.replace("/api/team/", "").replace("/timeline", "")
            with self._conn() as conn:
                rows = conn.execute(
                    """
                    SELECT season_id, position, finish_percentile, promoted_auto, promoted_playoff, top6_flag
                    FROM season_team_table
                    WHERE team_id = ?
                    ORDER BY season_id;
                    """,
                    (team_id,),
                ).fetchall()
            _json_response(self, {"rows": [dict(r) for r in rows]})
            return

        if path.startswith("/api/team/") and path.endswith("/context"):
            team_id = path.replace("/api/team/", "").replace("/context", "")
            with self._conn() as conn:
                managers = conn.execute(
                    """
                    SELECT season_id, manager_name, from_date, to_date, source_confidence
                    FROM managers_by_season
                    WHERE team_id = ?
                    ORDER BY season_id DESC;
                    """,
                    (team_id,),
                ).fetchall()
                scorers = conn.execute(
                    """
                    SELECT p.player_name, s.season_id, s.goals, s.assists, s.source_confidence
                    FROM player_season_team_stats s
                    JOIN players p ON p.player_id = s.player_id
                    WHERE s.team_id = ? AND s.is_team_top_scorer = 1
                    ORDER BY s.season_id DESC;
                    """,
                    (team_id,),
                ).fetchall()
            _json_response(self, {"managers": [dict(r) for r in managers], "top_scorers": [dict(r) for r in scorers]})
            return

        if path.startswith("/api/season/") and path.endswith("/compare"):
            season_id = path.replace("/api/season/", "").replace("/compare", "")
            query = parse_qs(parsed.query)
            slice_name = (query.get("slice") or ["all"])[0]
            where = "WHERE s.season_id = ?"
            params: tuple = (season_id,)
            if slice_name == "top6":
                where += " AND s.top6_flag = 1"
            elif slice_name == "promoted":
                where += " AND (s.promoted_auto = 1 OR s.promoted_playoff = 1)"
            elif slice_name == "relegated":
                where += " AND s.relegated = 1"
            with self._conn() as conn:
                rows = conn.execute(
                    f"""
                    SELECT s.*, t.team_name_canonical
                    FROM season_team_table s
                    JOIN teams t ON t.team_id = s.team_id
                    {where}
                    ORDER BY s.position;
                    """,
                    params,
                ).fetchall()
            _json_response(self, {"season_id": season_id, "slice": slice_name, "rows": [dict(r) for r in rows]})
            return

        _json_response(self, {"error": "not_found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                _json_response(self, {"error": "invalid_json"}, status=400)
                return
        else:
            payload = {}

        if path == "/api/column/generate":
            prompt = payload.get("prompt", "")
            with self._conn() as conn:
                schema_rows = conn.execute("SELECT sql FROM sqlite_master WHERE type='table';").fetchall()
                schema_sql = "\\n\\n".join(r["sql"] for r in schema_rows if r["sql"])

            settings = get_settings()
            
            # System prompt is shared between providers
            system_prompt = f"""You are a SQLite data warehouse expert creating custom metrics.
Here is the current database schema:
```sql
{schema_sql}
```
The user will provide a metric description. You must generate a SQLite SELECT query that computes this metric.
The query MUST return identifier columns (e.g., `team_id` and/or `season_id`) and a computed column named EXACTLY `value`.
You must return only a valid JSON response matching this exact structure, with no formatting outside the JSON:
{{
  "name": "Short, human-readable column name",
  "description": "Short explanation of calculation",
  "sql": "The raw SQLite SELECT query."
}}"""

            try:
                if settings.llm_provider == "groq" or (not settings.anthropic_api_key and settings.groq_api_key):
                    if not settings.groq_api_key:
                        _json_response(self, {"error": "GROQ_API_KEY not configured"}, status=500)
                        return
                    client = groq.Groq(api_key=settings.groq_api_key)
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    text = response.choices[0].message.content
                else:
                    if not settings.anthropic_api_key:
                        _json_response(self, {"error": "ANTHROPIC_API_KEY not configured"}, status=500)
                        return
                    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                    response = client.messages.create(
                        model="claude-3-7-sonnet-20250219",
                        max_tokens=1000,
                        system=system_prompt,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    text = response.content[0].text
                
                if text.startswith("```json"): text = text[7:]
                if text.startswith("```"): text = text[3:]
                if text.endswith("```"): text = text[:-3]
                parsed_json = json.loads(text.strip())
                _json_response(self, parsed_json)
            except Exception as e:
                _json_response(self, {"error": str(e)}, status=500)
            return

        if path == "/api/column/preview":
            sql = payload.get("sql", "").strip()
            upper_sql = sql.upper()
            forbidden = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CREATE ", "REPLACE ", "PRAGMA "]
            if any(f in upper_sql for f in forbidden):
                _json_response(self, {"error": "SQL execution error: Only SELECT statements are allowed."}, status=400)
                return

            try:
                with self._conn() as conn:
                    rows = conn.execute(sql).fetchall()
                    _json_response(self, {"rows": [dict(r) for r in rows], "count": len(rows)})
            except Exception as e:
                _json_response(self, {"error": f"SQL Error: {str(e)}"}, status=400)
            return

        _json_response(self, {"error": "not_found"}, status=404)


def serve(db_path: Path, host: str = "127.0.0.1", port: int = 8080) -> None:
    web_root = Path(__file__).resolve().parents[2] / "web"

    class _Handler(WarehouseApiHandler):
        pass

    _Handler.db_path = db_path
    _Handler.web_root = web_root
    server = HTTPServer((host, port), _Handler)
    print(f"Serving UI and API on http://{host}:{port}")
    server.serve_forever()

