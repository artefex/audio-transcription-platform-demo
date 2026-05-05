from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
