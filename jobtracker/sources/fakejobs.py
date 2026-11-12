"""Fonte 1: web scraping de HTML.

Usa o site https://realpython.github.io/fake-jobs/, feito para treinar scraping
(vagas fictícias, 100 por página). Como o site não tem busca, o filtro por
palavra-chave é feito aqui, depois do parsing.
"""
from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from jobtracker.http import build_session, fetch_text
from jobtracker.models import Job

NAME = "fakejobs"
URL = "https://realpython.github.io/fake-jobs/"

logger = logging.getLogger(__name__)


def _id_from_url(url: str) -> str:
    """'.../jobs/senior-python-developer-0.html' -> 'senior-python-developer-0'."""
    last = url.rstrip("/").rsplit("/", 1)[-1]
    return last.removesuffix(".html")


def parse_jobs(html: str) -> list[Job]:
    """Extrai as vagas de uma página HTML."""
    soup = BeautifulSoup(html, "lxml")
    jobs: dict[str, Job] = {}

    for card in soup.select("div.card"):
        title = card.select_one("h2.title")
        company = card.select_one("h3.company")
        location = card.select_one("p.location")
        posted = card.select_one("time")
        links = card.select("a.card-footer-item")
        apply_link = next((a for a in links if a.get_text(strip=True).lower() == "apply"), None)
        apply_link = apply_link or (links[-1] if links else None)

        if not (title and company and apply_link and apply_link.get("href")):
            logger.warning("Card incompleto ignorado")
            continue

        url = apply_link["href"].strip()
        external_id = _id_from_url(url)
        jobs[external_id] = Job(
            source=NAME,
            external_id=external_id,
            title=title.get_text(strip=True),
            company=company.get_text(strip=True),
            location=location.get_text(strip=True) if location else "",
            url=url,
            posted_date=(posted.get("datetime") or posted.get_text(strip=True)) if posted else None,
        )
    return list(jobs.values())


def collect(session=None, query: str | None = None) -> list[Job]:
    session = session or build_session()
    jobs = parse_jobs(fetch_text(session, URL))
    if query:
        q = query.lower()
        jobs = [j for j in jobs if q in j.title.lower() or q in j.company.lower()]
    return jobs
