import csv

import pytest
from openpyxl import load_workbook

from jobtracker import db
from jobtracker.export import export
from jobtracker.models import Job


@pytest.fixture
def rows():
    conn = db.connect(":memory:")
    db.save_run(conn, "s", [Job("s", "1", "Dev Python", "Acme", "Brasil", "http://x/1", "2026-11-01")])
    return db.search_jobs(conn)


def test_export_excel(rows, tmp_path):
    out = export(rows, tmp_path / "v.xlsx")
    ws = load_workbook(out)["Vagas"]
    assert ws["A1"].value == "Título"
    assert ws["A2"].value == "Dev Python"
    assert ws["E2"].value == "Ativa"
    assert ws["H2"].hyperlink.target == "http://x/1"
    assert ws.freeze_panes == "A2"


def test_export_csv(rows, tmp_path):
    out = export(rows, tmp_path / "v.csv")
    data = list(csv.reader(open(out, encoding="utf-8-sig"), delimiter=";"))
    assert data[0][0] == "Título" and data[1][1] == "Acme"


def test_export_invalid_extension(rows, tmp_path):
    with pytest.raises(ValueError):
        export(rows, tmp_path / "v.txt")
