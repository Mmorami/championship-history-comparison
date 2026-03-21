CREATE TABLE IF NOT EXISTS matches (
    match_id TEXT PRIMARY KEY,
    season_id TEXT NOT NULL,
    date TEXT NOT NULL,
    home_team_id TEXT NOT NULL,
    away_team_id TEXT NOT NULL,
    home_goals INTEGER NOT NULL,
    away_goals INTEGER NOT NULL,
    result TEXT NOT NULL, -- 'H' for Home Win, 'D' for Draw, 'A' for Away Win
    FOREIGN KEY(season_id) REFERENCES seasons(season_id),
    FOREIGN KEY(home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY(away_team_id) REFERENCES teams(team_id)
);

CREATE INDEX IF NOT EXISTS idx_matches_season_home ON matches(season_id, home_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_season_away ON matches(season_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date);
