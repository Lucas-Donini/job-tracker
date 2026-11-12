from pathlib import Path

from jobtracker.sources import fakejobs, remotive

HTML = (Path(__file__).parent / "fixtures" / "fakejobs.html").read_text(encoding="utf-8")


def test_fakejobs_parse():
    jobs = fakejobs.parse_jobs(HTML)
    assert len(jobs) == 3  # card quebrado é ignorado
    j = jobs[0]
    assert j.title == "Senior Python Developer"
    assert j.company == "Payne, Roberts and Davis"
    assert j.external_id == "senior-python-developer-0"
    assert j.url.endswith("senior-python-developer-0.html")
    assert j.posted_date == "2021-04-08"


def test_fakejobs_collect_filters_by_query(monkeypatch):
    monkeypatch.setattr(fakejobs, "fetch_text", lambda session, url: HTML)
    jobs = fakejobs.collect(session=object(), query="python")
    assert [j.external_id for j in jobs] == ["senior-python-developer-0", "python-data-analyst-2"]


def test_remotive_parse():
    payload = {
        "jobs": [
            {"id": 101, "title": " Backend Python ", "company_name": "Acme", "url": "https://r/101",
             "candidate_required_location": "Brazil", "publication_date": "2026-11-10T08:00:00"},
            {"id": 102, "company_name": "Sem título", "url": "https://r/102"},  # incompleto
        ]
    }
    jobs = remotive.parse_jobs(payload)
    assert len(jobs) == 1
    assert jobs[0].title == "Backend Python"
    assert jobs[0].posted_date == "2026-11-10"
    assert jobs[0].external_id == "101"


def test_remotive_parse_empty():
    assert remotive.parse_jobs({}) == []
    assert remotive.parse_jobs(None) == []
