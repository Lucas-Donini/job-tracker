from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    """Uma vaga coletada de qualquer fonte."""

    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    posted_date: str | None = None  # formato AAAA-MM-DD
