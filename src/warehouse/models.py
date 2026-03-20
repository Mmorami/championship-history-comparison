from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamSeasonRow:
    season_id: str
    team_name: str
    position: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int
    promoted_auto: bool
    promoted_playoff: bool
    playoff_participant: bool
    relegated: bool
    quality_grade: str = "A"

