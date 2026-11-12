"""Exportação das vagas para Excel (.xlsx) ou CSV."""
from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HEADERS = ["Título", "Empresa", "Local", "Publicada em", "Status", "Vista pela 1ª vez", "Fonte", "Link"]
WIDTHS = [42, 30, 26, 14, 11, 20, 11, 60]
THIN = Side(style="thin", color="BFBFBF")


def _as_row(job) -> list:
    return [
        job["title"], job["company"], job["location"], job["posted_date"] or "",
        "Ativa" if job["active"] else "Encerrada", job["first_seen"], job["source"], job["url"],
    ]


def export_csv(rows, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: Excel lê acentos
        writer = csv.writer(f, delimiter=";")
        writer.writerow(HEADERS)
        writer.writerows(_as_row(r) for r in rows)
    return path


def export_excel(rows, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Vagas"
    ws.append(HEADERS)
    for col in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(name="Arial", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", start_color="1F3864")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(col)].width = WIDTHS[col - 1]

    for i, job in enumerate(rows, start=2):
        ws.append(_as_row(job))
        ws.cell(row=i, column=8).hyperlink = job["url"]
        for col in range(1, len(HEADERS) + 1):
            cell = ws.cell(row=i, column=col)
            cell.font = (
                Font(name="Arial", color="0563C1", underline="single") if col == 8 else Font(name="Arial")
            )
            cell.border = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEADERS))}{max(len(rows) + 1, 2)}"
    wb.save(path)
    return path


def export(rows, path: str | Path) -> Path:
    """Escolhe o formato pela extensão do arquivo."""
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return export_csv(rows, path)
    if suffix == ".xlsx":
        return export_excel(rows, path)
    raise ValueError("Use uma extensão .xlsx ou .csv")
