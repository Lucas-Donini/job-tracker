"""Camada de banco de dados (SQLite, biblioteca padrão do Python).

Ideia central: cada coleta é uma "execução" (run). Para cada vaga guardamos
quando foi vista pela primeira vez, quando foi vista pela última vez e se
ainda está ativa. Vaga que some da fonte é marcada como encerrada.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jobtracker.models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    query       TEXT,
    started_at  TEXT NOT NULL,
    found       INTEGER NOT NULL DEFAULT 0,
    new         INTEGER NOT NULL DEFAULT 0,
    closed      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    external_id  TEXT NOT NULL,
    title        TEXT NOT NULL,
    company      TEXT NOT NULL,
    location     TEXT NOT NULL DEFAULT '',
    url          TEXT NOT NULL,
    posted_date  TEXT,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL,
    first_run_id INTEGER NOT NULL,
    last_run_id  INTEGER NOT NULL,
    active       INTEGER NOT NULL DEFAULT 1,
    UNIQUE (source, external_id)
);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (active);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs (company);
"""


@dataclass
class RunStats:
    run_id: int
    found: int
    new: int
    updated: int
    closed: int


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect(path: str | Path = "data/jobs.db") -> sqlite3.Connection:
    """Abre (e cria, se preciso) o banco."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_run(
    conn: sqlite3.Connection,
    source: str,
    jobs: list[Job],
    query: str | None = None,
    close_missing: bool = True,
    now: str | None = None,
) -> RunStats:
    """Grava uma coleta inteira de forma atômica.

    - vaga inédita            -> inserida (new)
    - vaga já conhecida       -> atualizada e reativada
    - vaga que sumiu da fonte -> marcada como encerrada, mas só se
      `close_missing=True` e a coleta trouxe resultados (coleta vazia
      costuma ser falha, não "todas as vagas fecharam").
    """
    now = now or _now()
    new = 0
    with conn:  # transação: ou grava tudo ou nada
        run_id = conn.execute(
            "INSERT INTO runs (source, query, started_at) VALUES (?, ?, ?)",
            (source, query, now),
        ).lastrowid

        for job in jobs:
            cur = conn.execute(
                """UPDATE jobs SET title=?, company=?, location=?, url=?, posted_date=?,
                          last_seen=?, last_run_id=?, active=1
                   WHERE source=? AND external_id=?""",
                (job.title, job.company, job.location, job.url, job.posted_date,
                 now, run_id, job.source, job.external_id),
            )
            if cur.rowcount == 0:
                conn.execute(
                    """INSERT INTO jobs (source, external_id, title, company, location, url,
                                         posted_date, first_seen, last_seen, first_run_id, last_run_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (job.source, job.external_id, job.title, job.company, job.location,
                     job.url, job.posted_date, now, now, run_id, run_id),
                )
                new += 1

        closed = 0
        if close_missing and jobs:
            closed = conn.execute(
                "UPDATE jobs SET active=0 WHERE source=? AND active=1 AND last_run_id != ?",
                (source, run_id),
            ).rowcount

        conn.execute(
            "UPDATE runs SET found=?, new=?, closed=? WHERE id=?",
            (len(jobs), new, closed, run_id),
        )
    return RunStats(run_id=run_id, found=len(jobs), new=new, updated=len(jobs) - new, closed=closed)


def search_jobs(
    conn: sqlite3.Connection,
    keyword: str | None = None,
    company: str | None = None,
    location: str | None = None,
    source: str | None = None,
    only_active: bool = True,
    only_new: bool = False,
    limit: int | None = 50,
) -> list[sqlite3.Row]:
    """Busca vagas com filtros combináveis (LIKE é case-insensitive no SQLite)."""
    where, params = [], []
    if keyword:
        where.append("(title LIKE ? OR company LIKE ?)")
        params += [f"%{keyword}%"] * 2
    if company:
        where.append("company LIKE ?")
        params.append(f"%{company}%")
    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")
    if source:
        where.append("source = ?")
        params.append(source)
    if only_active:
        where.append("active = 1")
    if only_new:  # vagas inéditas na última coleta da respectiva fonte
        where.append("first_run_id = (SELECT MAX(id) FROM runs r WHERE r.source = jobs.source)")

    sql = "SELECT * FROM jobs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY posted_date DESC, title ASC"
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def get_stats(conn: sqlite3.Connection) -> dict:
    """Números gerais do banco, para o comando `stats`."""
    one = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    return {
        "total": one("SELECT COUNT(*) FROM jobs"),
        "ativas": one("SELECT COUNT(*) FROM jobs WHERE active = 1"),
        "encerradas": one("SELECT COUNT(*) FROM jobs WHERE active = 0"),
        "coletas": one("SELECT COUNT(*) FROM runs"),
        "por_fonte": {
            r["source"]: r["n"]
            for r in conn.execute("SELECT source, COUNT(*) n FROM jobs WHERE active=1 GROUP BY source")
        },
        "top_empresas": [
            (r["company"], r["n"])
            for r in conn.execute(
                "SELECT company, COUNT(*) n FROM jobs WHERE active=1 "
                "GROUP BY company ORDER BY n DESC, company LIMIT 5"
            )
        ],
        "ultima_coleta": conn.execute(
            "SELECT started_at FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone(),
    }
