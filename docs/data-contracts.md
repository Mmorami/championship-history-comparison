# Data Contracts

## Core Contract: `season_team_table`

Required fields (hard fail if missing):

- `season_id`
- `team_id`
- `position`
- `played`
- `wins`
- `draws`
- `losses`
- `goals_for`
- `goals_against`
- `goal_diff`
- `points`
- `ppg`
- `gd_per_game`
- `finish_percentile`
- `promoted_auto`
- `promoted_playoff`
- `playoff_participant`
- `promotion_status`
- `quality_grade`

Optional fields:

- `relegated` (nullable source-side, normalized to boolean in warehouse)

## Playoff Contract: `playoffs`

Required:

- `season_id`
- `team_id`
- `playoff_stage_reached` (`semi_final|final|winner`)
- `quality_grade`

Optional:

- `playoff_matches`
- `playoff_wins`
- `playoff_losses`

## Manager Contract: `managers_by_season`

Required:

- `season_id`
- `team_id`
- `manager_name`
- `is_primary_manager`
- `source_confidence`

Optional:

- `from_date`
- `to_date`

## Player Contract: `player_season_team_stats`

Required:

- `season_id`
- `team_id`
- `player_id`
- `is_team_top_scorer`
- `source_confidence`
- `assists_coverage_complete_for_season`

Optional:

- `appearances`
- `goals`
- `assists`

## Confidence Rules

- `A`: verified primary-source core stats; cross-check passed or deterministic derivation from complete primary data.
- `B`: reliable backup or inferred from consistent related facts.
- `C`: partially complete data or single-source non-core context.
- `D`: missing/incomplete or development fallback data.
