CREATE TABLE IF NOT EXISTS ref_quality_grade (
    grade TEXT PRIMARY KEY CHECK (grade IN ('A', 'B', 'C', 'D'))
);

INSERT OR IGNORE INTO ref_quality_grade(grade) VALUES ('A'), ('B'), ('C'), ('D');

CREATE TABLE IF NOT EXISTS seasons (
    season_id TEXT PRIMARY KEY,
    competition_name TEXT NOT NULL,
    tier_level INTEGER NOT NULL CHECK (tier_level = 2),
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    teams_count INTEGER NOT NULL,
    matches_per_team_planned INTEGER NOT NULL,
    is_complete INTEGER NOT NULL CHECK (is_complete IN (0, 1)),
    data_cutoff_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    team_name_canonical TEXT NOT NULL UNIQUE,
    country TEXT NOT NULL DEFAULT 'England',
    founded_year INTEGER
);

CREATE TABLE IF NOT EXISTS team_aliases (
    alias_name TEXT PRIMARY KEY,
    team_id TEXT NOT NULL REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS season_team_table (
    season_id TEXT NOT NULL REFERENCES seasons(season_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    position INTEGER NOT NULL,
    played INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    draws INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    goal_diff INTEGER NOT NULL,
    points INTEGER NOT NULL,
    ppg REAL NOT NULL,
    gd_per_game REAL NOT NULL,
    finish_percentile REAL NOT NULL,
    promoted_auto INTEGER NOT NULL CHECK (promoted_auto IN (0, 1)),
    promoted_playoff INTEGER NOT NULL CHECK (promoted_playoff IN (0, 1)),
    playoff_participant INTEGER NOT NULL CHECK (playoff_participant IN (0, 1)),
    relegated INTEGER NOT NULL CHECK (relegated IN (0, 1)),
    promotion_status TEXT NOT NULL CHECK (promotion_status IN ('none', 'auto', 'playoff')),
    top6_flag INTEGER NOT NULL CHECK (top6_flag IN (0, 1)),
    quality_grade TEXT NOT NULL REFERENCES ref_quality_grade(grade),
    PRIMARY KEY (season_id, team_id)
);

CREATE INDEX IF NOT EXISTS idx_stt_season_position ON season_team_table(season_id, position);
CREATE INDEX IF NOT EXISTS idx_stt_promoted ON season_team_table(promoted_auto, promoted_playoff);

CREATE TABLE IF NOT EXISTS playoffs (
    season_id TEXT NOT NULL REFERENCES seasons(season_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    playoff_stage_reached TEXT NOT NULL CHECK (playoff_stage_reached IN ('semi_final', 'final', 'winner')),
    playoff_matches INTEGER,
    playoff_wins INTEGER,
    playoff_losses INTEGER,
    quality_grade TEXT NOT NULL REFERENCES ref_quality_grade(grade),
    PRIMARY KEY (season_id, team_id)
);

CREATE TABLE IF NOT EXISTS managers_by_season (
    manager_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id TEXT NOT NULL REFERENCES seasons(season_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    manager_name TEXT NOT NULL,
    from_date TEXT,
    to_date TEXT,
    is_primary_manager INTEGER NOT NULL CHECK (is_primary_manager IN (0, 1)),
    source_confidence TEXT NOT NULL REFERENCES ref_quality_grade(grade)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_managers_unique
ON managers_by_season(season_id, team_id, manager_name, from_date, to_date);

CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    player_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS player_season_team_stats (
    season_id TEXT NOT NULL REFERENCES seasons(season_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    player_id TEXT NOT NULL REFERENCES players(player_id),
    appearances INTEGER,
    goals INTEGER,
    assists INTEGER,
    is_team_top_scorer INTEGER NOT NULL CHECK (is_team_top_scorer IN (0, 1)),
    source_confidence TEXT NOT NULL REFERENCES ref_quality_grade(grade),
    assists_coverage_complete_for_season INTEGER NOT NULL CHECK (assists_coverage_complete_for_season IN (0, 1)),
    PRIMARY KEY (season_id, team_id, player_id)
);

CREATE TABLE IF NOT EXISTS data_lineage (
    lineage_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_key TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    fetched_at_utc TEXT NOT NULL,
    checksum_raw TEXT,
    quality_grade TEXT NOT NULL REFERENCES ref_quality_grade(grade),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_lineage_entity ON data_lineage(entity_type, entity_key);

CREATE TABLE IF NOT EXISTS scoring_runs (
    run_id TEXT PRIMARY KEY,
    scoring_version TEXT NOT NULL,
    started_at_utc TEXT NOT NULL,
    completed_at_utc TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS team_ranking_snapshot (
    run_id TEXT NOT NULL REFERENCES scoring_runs(run_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    overall_score REAL NOT NULL,
    performance_score REAL NOT NULL,
    outcomes_score REAL NOT NULL,
    consistency_score REAL NOT NULL,
    promotions_total INTEGER NOT NULL,
    promotion_auto_total INTEGER NOT NULL,
    promotion_playoff_total INTEGER NOT NULL,
    top6_total INTEGER NOT NULL,
    avg_ppg_promotion REAL NOT NULL,
    avg_finish_percentile_promotion REAL NOT NULL,
    playoff_conversion REAL NOT NULL,
    PRIMARY KEY (run_id, team_id)
);
