"""Sessão HTTP com boas práticas: User-Agent, timeout e retry."""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "job-tracker/1.0 (projeto de portfolio)"


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_text(session: requests.Session, url: str, timeout: int = 15) -> str:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def fetch_json(session: requests.Session, url: str, params: dict | None = None, timeout: int = 15):
    response = session.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()
