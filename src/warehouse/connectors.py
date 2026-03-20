from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SourceConfig:
    name: str
    base_url: str


SOURCES: list[SourceConfig] = [
    SourceConfig(name="worldfootball", base_url="https://www.worldfootball.net"),
    SourceConfig(name="soccerway", base_url="https://int.soccerway.com"),
    SourceConfig(name="wikipedia", base_url="https://en.wikipedia.org"),
]


def fetch_url(url: str, timeout_s: int = 30) -> str:
    req = Request(url, headers={"User-Agent": "champ-history-warehouse/0.1"})
    with urlopen(req, timeout=timeout_s) as response:
        return response.read().decode("utf-8", errors="replace")


def store_raw_payload(raw_data_dir: Path, source_name: str, entity: str, season_id: str, payload: str, source_url: str) -> dict[str, Any]:
    fetched_at = datetime.now(timezone.utc).isoformat()
    checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    target_dir = raw_data_dir / source_name / entity / season_id
    target_dir.mkdir(parents=True, exist_ok=True)
    raw_path = target_dir / f"{fetched_at.replace(':', '-')}.json"
    envelope = {
        "source_name": source_name,
        "source_url": source_url,
        "season_id": season_id,
        "fetched_at_utc": fetched_at,
        "checksum_raw": checksum,
        "payload": payload,
    }
    raw_path.write_text(json.dumps(envelope), encoding="utf-8")
    return envelope

