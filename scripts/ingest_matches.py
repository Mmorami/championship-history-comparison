import csv
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
import sys

# Ensure warehouse package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from warehouse.canonicalize import normalize_team_name, team_id_from_name
from warehouse.config import get_settings
from warehouse.db import connect
from warehouse.migrations import apply_migrations

def parse_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return date_str

def main():
    settings = get_settings()
    conn = connect(settings.db_path)
    
    # Ensure migrations are applied first
    apply_migrations(conn, Path("migrations"))
    
    raw_data_dir = settings.raw_data_dir / "football_data" / "season_matches_csv"
    if not raw_data_dir.exists():
        print(f"Data dir {raw_data_dir} does not exist.")
        return
        
    for season_dir in raw_data_dir.iterdir():
        if not season_dir.is_dir():
            continue
            
        season_id = season_dir.name
        
        json_files = sorted(season_dir.glob("*.json"))
        if not json_files:
            continue
            
        latest_file = json_files[-1]
        with open(latest_file, "r") as f:
            data = json.load(f)
            
        payload = data.get("payload", "")
        lines = payload.splitlines()
        if not lines:
            continue
            
        reader = csv.DictReader(lines)
        
        inserted = 0
        skipped = 0
        
        for row in reader:
            if not row:
                continue
                
            date_str = row.get("Date", "")
            if not date_str:
                continue
                
            match_date = parse_date(date_str)
            home_team_raw = row.get("HomeTeam", "")
            away_team_raw = row.get("AwayTeam", "")
            
            home_goals = row.get("FTHG")
            away_goals = row.get("FTAG")
            result = row.get("FTR")
            
            if not home_team_raw or not away_team_raw or result not in ("H", "D", "A") or home_goals is None or away_goals is None:
                skipped += 1
                continue
                
            home_team_id = team_id_from_name(normalize_team_name(home_team_raw))
            away_team_id = team_id_from_name(normalize_team_name(away_team_raw))
            
            conn.execute("INSERT OR IGNORE INTO teams(team_id, team_name_canonical) VALUES (?, ?)", (home_team_id, normalize_team_name(home_team_raw)))
            conn.execute("INSERT OR IGNORE INTO teams(team_id, team_name_canonical) VALUES (?, ?)", (away_team_id, normalize_team_name(away_team_raw)))

            match_id_str = f"{season_id}_{match_date}_{home_team_id}_{away_team_id}"
            match_id = hashlib.md5(match_id_str.encode()).hexdigest()
            
            conn.execute(
                """
                INSERT OR REPLACE INTO matches(
                    match_id, season_id, date, home_team_id, away_team_id, home_goals, away_goals, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (match_id, season_id, match_date, home_team_id, away_team_id, int(home_goals), int(away_goals), result)
            )
            inserted += 1
            
        conn.commit()
        print(f"Ingested {inserted} matches (skipped {skipped}) for season {season_id} from {latest_file.name}")

if __name__ == "__main__":
    main()
