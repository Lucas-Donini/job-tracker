import pytest

from jobtracker import db
from jobtracker.models import Job


def J(i, title="Dev Python", company="Acme", location="Brasil", posted="2026-11-01"):
    return Job("s", str(i), title, company, location, f"http://x/{i}", posted)


@pytest.fixture
def conn():
    c = db.connect(":memory:")
    yield c
    c.close()


def test_first_run_all_new(conn):
    stats = db.save_run(conn, "s", [J(1), J(2)])
    assert (stats.found, stats.new, stats.updated, stats.closed) == (2, 2, 0, 0)


def test_second_run_is_idempotent(conn):
    db.save_run(conn, "s", [J(1), J(2)])
    stats = db.save_run(conn, "s", [J(1), J(2)])
    assert (stats.new, stats.updated, stats.closed) == (0, 2, 0)
    assert db.get_stats(conn)["total"] == 2  # sem duplicar


def test_missing_jobs_are_closed_and_reopened(conn):
    db.save_run(conn, "s", [J(1), J(2)])
    stats = db.save_run(conn, "s", [J(1)])
    assert stats.closed == 1
    assert {r["external_id"] for r in db.search_jobs(conn)} == {"1"}
    assert len(db.search_jobs(conn, only_active=False)) == 2

    db.save_run(conn, "s", [J(1), J(2)])  # vaga voltou
    assert {r["external_id"] for r in db.search_jobs(conn)} == {"1", "2"}


def test_partial_run_does_not_close(conn):
    db.save_run(conn, "s", [J(1), J(2)])
    stats = db.save_run(conn, "s", [J(1)], query="python", close_missing=False)
    assert stats.closed == 0
    assert len(db.search_jobs(conn)) == 2


def test_empty_run_does_not_close(conn):
    db.save_run(conn, "s", [J(1)])
    assert db.save_run(conn, "s", []).closed == 0
    assert len(db.search_jobs(conn)) == 1


def test_closing_is_per_source(conn):
    db.save_run(conn, "s", [J(1)])
    other = Job("o", "9", "Outra", "Beta", "", "http://o/9")
    db.save_run(conn, "o", [other])
    assert len(db.search_jobs(conn)) == 2  # coletar 'o' não fecha vagas de 's'


def test_existing_job_is_updated(conn):
    db.save_run(conn, "s", [J(1, title="Antigo")])
    db.save_run(conn, "s", [J(1, title="Novo título")])
    assert db.search_jobs(conn)[0]["title"] == "Novo título"


def test_search_filters(conn):
    db.save_run(conn, "s", [
        J(1, title="Python Dev", company="Acme", location="Pelotas"),
        J(2, title="Java Dev", company="Beta", location="Porto Alegre"),
    ])
    assert len(db.search_jobs(conn, keyword="python")) == 1
    assert len(db.search_jobs(conn, company="beta")) == 1
    assert len(db.search_jobs(conn, location="pelotas")) == 1
    assert len(db.search_jobs(conn, keyword="python", company="beta")) == 0


def test_only_new_in_last_run(conn):
    db.save_run(conn, "s", [J(1)])
    db.save_run(conn, "s", [J(1), J(2)])
    new = db.search_jobs(conn, only_new=True)
    assert [r["external_id"] for r in new] == ["2"]


def test_get_stats(conn):
    db.save_run(conn, "s", [J(1, company="Acme"), J(2, company="Acme"), J(3, company="Beta")])
    s = db.get_stats(conn)
    assert s["ativas"] == 3 and s["coletas"] == 1
    assert s["top_empresas"][0] == ("Acme", 2)
