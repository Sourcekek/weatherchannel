"""Common types and helpers shared across models."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeAlias

RunId: TypeAlias = str


class CityId(StrEnum):
    NYC = "nyc"
    CHICAGO = "chicago"
    SEATTLE = "seattle"
    ATLANTA = "atlanta"
    DALLAS = "dallas"


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()
