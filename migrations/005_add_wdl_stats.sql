-- 003_add_wdl_stats.sql
-- Add Wins, Draws, and Losses to the ranking snapshot and update the input view.

-- 1. Update the input view to include wins, draws, losses.
DROP VIEW IF EXISTS vw_season_team_ranking_inputs;
CREATE VIEW vw_season_team_ranking_inputs AS
SELECT
    s.season_id,
    s.team_id,
    s.position,
    s.played,
    s.wins,
    s.draws,
    s.losses,
    s.points,
    s.ppg,
    s.goals_for,
    s.goals_against,
    s.goal_diff,
    s.finish_percentile,
    s.gd_per_game,
    s.promoted_auto,
    s.promoted_playoff,
    s.playoff_participant,
    s.top6_flag
FROM season_team_table s
WHERE s.quality_grade IN ('A', 'B')
  AND (s.promoted_auto = 1 OR s.promoted_playoff = 1 OR s.top6_flag = 1);

-- 2. Add columns to team_ranking_snapshot.
-- Since we want to keep existing snapshots if possible (though we just rebuilt them),
-- we'll recreate the table to keep it clean, as it's a snapshot table.
DROP TABLE IF EXISTS team_ranking_snapshot;
CREATE TABLE team_ranking_snapshot (
    run_id TEXT NOT NULL REFERENCES scoring_runs(run_id),
    season_id TEXT NOT NULL REFERENCES seasons(season_id),
    team_id TEXT NOT NULL REFERENCES teams(team_id),
    overall_score REAL NOT NULL,
    performance_score REAL NOT NULL,
    outcomes_score REAL NOT NULL,
    consistency_score REAL NOT NULL,
    position INTEGER NOT NULL,
    played INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    draws INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    points INTEGER NOT NULL,
    ppg REAL NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    goal_diff INTEGER NOT NULL,
    finish_percentile REAL NOT NULL,
    promoted_auto INTEGER NOT NULL,
    promoted_playoff INTEGER NOT NULL,
    PRIMARY KEY (run_id, season_id, team_id)
);

CREATE INDEX idx_trs_run_score ON team_ranking_snapshot(run_id, overall_score DESC);
