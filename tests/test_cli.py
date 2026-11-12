from jobtracker import cli
from jobtracker.models import Job


def fake_source(jobs):
    return lambda session=None, query=None: jobs


JOBS = [
    Job("fakejobs", "1", "Dev Python", "Acme", "Pelotas", "http://x/1", "2026-11-01"),
    Job("fakejobs", "2", "Analista de Dados", "Beta", "Porto Alegre", "http://x/2", "2026-11-02"),
]


def run(tmp_path, *args):
    return cli.main(["--db", str(tmp_path / "t.db"), *args])


def test_collect_list_stats_export_flow(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(cli.SOURCES, "fakejobs", fake_source(JOBS))

    assert run(tmp_path, "collect") == 0
    assert "2 vagas | 2 novas" in capsys.readouterr().out

    assert run(tmp_path, "collect") == 0  # segunda coleta: nada novo
    assert "0 novas | 2 já conhecidas" in capsys.readouterr().out

    assert run(tmp_path, "list", "-k", "python") == 0
    out = capsys.readouterr().out
    assert "Dev Python" in out and "Analista" not in out

    assert run(tmp_path, "stats") == 0
    assert "2 ativas" in capsys.readouterr().out

    out_file = tmp_path / "v.xlsx"
    assert run(tmp_path, "export", "-o", str(out_file)) == 0
    assert out_file.exists()


def test_collect_with_query_does_not_close(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(cli.SOURCES, "fakejobs", fake_source(JOBS))
    run(tmp_path, "collect")
    monkeypatch.setitem(cli.SOURCES, "fakejobs", fake_source(JOBS[:1]))
    run(tmp_path, "collect", "-q", "python")
    assert "0 encerradas" in capsys.readouterr().out


def test_collect_network_error(tmp_path, monkeypatch, capsys):
    def boom(session=None, query=None):
        raise ConnectionError("sem internet")

    monkeypatch.setitem(cli.SOURCES, "fakejobs", boom)
    assert run(tmp_path, "collect") == 1
    assert "sem internet" in capsys.readouterr().err


def test_export_empty_and_bad_extension(tmp_path, monkeypatch):
    assert run(tmp_path, "export") == 1  # banco vazio
    monkeypatch.setitem(cli.SOURCES, "fakejobs", fake_source(JOBS))
    run(tmp_path, "collect")
    assert run(tmp_path, "export", "-o", str(tmp_path / "v.txt")) == 2
