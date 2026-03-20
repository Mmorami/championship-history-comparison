# API Contracts

## 1) Leaderboard - Promotion Power

- Endpoint: `GET /api/v1/leaderboard`
- Response:
  - `metadata`
    - `run_id`
    - `generated_at_utc`
    - `data_cutoff_utc` (optional)
    - `quality_summary` (optional)
  - `rows[]`
    - `team_name_canonical`
    - `overall_score`
    - `performance_score`
    - `outcomes_score`
    - `consistency_score`
    - `promotions_total`
    - `promotion_auto_total`
    - `promotion_playoff_total`
    - `top6_total`
    - `avg_ppg_promotion`
    - `avg_finish_percentile_promotion`
    - `playoff_conversion`

## 2) Team Timeline

- Endpoint: `GET /api/v1/team/{team_id}/timeline`
- Response:
  - `metadata` block as above
  - `rows[]`
    - `season_id`
    - `finish_percentile`
    - `position`
    - `promoted_auto`
    - `promoted_playoff`
    - `top6_flag`

## 3) Season Comparator

- Endpoint: `GET /api/v1/seasons/{season_id}/compare?slice=all|top6|promoted`
- Response:
  - `metadata`
  - `rows[]`
    - full `season_team_table` fields for selected slice
  - `scatter[]`
    - `team_id`, `ppg`, `gd_per_game`, `goals_for`

## 4) Context Panel

- Endpoint: `GET /api/v1/team/{team_id}/context`
- Response:
  - `metadata`
  - `managers[]` with `source_confidence`
  - `top_scorers[]` with goals and confidence
  - `notable_alumni[]` optionally curated
