"""Fonte 2: API JSON pública do Remotive (vagas remotas reais).

Atribuição: vagas fornecidas por Remotive (https://remotive.com).
A API pede uso moderado (poucas consultas por dia) e que a origem seja citada,
então rode esta coleta com parcimônia.
"""
from __future__ import annotations

import logging

from jobtracker.http import build_session, fetch_json
from jobtracker.models import Job

NAME = "remotive"
API_URL = "https://remotive.com/api/remote-jobs"

logger = logging.getLogger(__name__)


def parse_jobs(payload: dict) -> list[Job]:
    """Converte o JSON da API em objetos Job."""
    jobs: dict[str, Job] = {}
    for item in (payload or {}).get("jobs", []):
        try:
            external_id = str(item["id"])
            jobs[external_id] = Job(
                source=NAME,
                external_id=external_id,
                title=str(item["title"]).strip(),
                company=str(item.get("company_name", "")).strip(),
                location=str(item.get("candidate_required_location", "")).strip(),
                url=str(item["url"]).strip(),
                posted_date=(item.get("publication_date") or "")[:10] or None,
            )
        except KeyError:
            logger.warning("Item incompleto ignorado: %s", item.get("id"))
    return list(jobs.values())


def collect(session=None, query: str | None = None) -> list[Job]:
    session = session or build_session()
    params = {"search": query} if query else None
    return parse_jobs(fetch_json(session, API_URL, params=params))
