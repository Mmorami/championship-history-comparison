from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    raw_data_dir: Path
    reports_dir: Path
    scoring_version: str
    football_data_api_key: str | None
    api_football_key: str | None


def get_settings() -> Settings:
    db_path = Path(os.getenv("WAREHOUSE_DB_PATH", "./data/warehouse.db"))
    raw_data_dir = Path(os.getenv("RAW_DATA_DIR", "./data/raw"))
    reports_dir = Path(os.getenv("REPORTS_DIR", "./data/reports"))
    scoring_version = os.getenv("SCORING_VERSION", "v1")
    football_data_api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    api_football_key = os.getenv("API_FOOTBALL_KEY")
    return Settings(
        db_path=db_path,
        raw_data_dir=raw_data_dir,
        reports_dir=reports_dir,
        scoring_version=scoring_version,
        football_data_api_key=football_data_api_key,
        api_football_key=api_football_key,
    )

