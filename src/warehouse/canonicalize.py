from __future__ import annotations

import re
from typing import Iterable


def normalize_team_name(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip())
    substitutions = {
        "QPR": "Queens Park Rangers",
        "Nottm Forest": "Nottingham Forest",
        "Sheff Utd": "Sheffield United",
        "Sheff Wed": "Sheffield Wednesday",
        "West Brom": "West Bromwich Albion",
    }
    return substitutions.get(cleaned, cleaned)


def team_id_from_name(name: str) -> str:
    canonical = normalize_team_name(name).lower()
    canonical = re.sub(r"[^a-z0-9]+", "-", canonical).strip("-")
    return f"team:{canonical}"


def season_id_from_years(start_year: int, end_year: int) -> str:
    return f"{start_year}-{str(end_year)[-2:]}"


def apply_aliases(name: str, aliases: dict[str, str]) -> str:
    return aliases.get(name, name)


def dedupe_names(names: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        n = normalize_team_name(name)
        if n not in seen:
            out.append(n)
            seen.add(n)
    return out

