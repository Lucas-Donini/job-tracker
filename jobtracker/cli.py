"""Interface de linha de comando: collect | list | stats | export."""
from __future__ import annotations

import argparse
import logging
import sys

from jobtracker import db
from jobtracker.export import export
from jobtracker.http import build_session
from jobtracker.sources import SOURCES


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jobtracker", description="Coleta e acompanha vagas de emprego.")
    p.add_argument("--db", default="data/jobs.db", help="caminho do banco SQLite (padrão: data/jobs.db)")
    p.add_argument("-v", "--verbose", action="store_true", help="logs detalhados")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("collect", help="coleta vagas de uma fonte e salva no banco")
    c.add_argument("-s", "--source", choices=sorted(SOURCES), default="fakejobs")
    c.add_argument("-q", "--query", help="palavra-chave (ex.: python)")

    def add_filters(sp):
        sp.add_argument("-k", "--keyword", help="busca no título ou empresa")
        sp.add_argument("--company", help="filtra por empresa")
        sp.add_argument("--location", help="filtra por local")
        sp.add_argument("-s", "--source", choices=sorted(SOURCES), help="filtra por fonte")
        sp.add_argument("--new", action="store_true", help="só vagas inéditas da última coleta")
        sp.add_argument("--all", action="store_true", help="inclui vagas encerradas")

    l = sub.add_parser("list", help="lista vagas do banco")
    add_filters(l)
    l.add_argument("-n", "--limit", type=int, default=20, help="máximo de linhas (padrão 20)")

    sub.add_parser("stats", help="mostra números gerais do banco")

    e = sub.add_parser("export", help="exporta vagas para .xlsx ou .csv")
    add_filters(e)
    e.add_argument("-o", "--output", default="output/vagas.xlsx", help="arquivo de saída (.xlsx ou .csv)")
    return p


def _filters(args) -> dict:
    return dict(
        keyword=args.keyword, company=args.company, location=args.location,
        source=args.source, only_active=not args.all, only_new=args.new,
    )


def cmd_collect(args, conn) -> int:
    print(f"Coletando da fonte '{args.source}'...")
    try:
        jobs = SOURCES[args.source](session=build_session(), query=args.query)
    except Exception as exc:  # noqa: BLE001 - erro de rede/API vira mensagem amigável
        print(f"Erro ao coletar: {exc}", file=sys.stderr)
        return 1

    if not jobs:
        print("Nenhuma vaga encontrada (nada foi alterado no banco).")
        return 0

    # Com filtro de palavra-chave a coleta é parcial: não dá para saber se
    # as demais vagas fecharam, então não marcamos nada como encerrado.
    stats = db.save_run(conn, args.source, jobs, query=args.query, close_missing=not args.query)
    print(
        f"[{args.source}] {stats.found} vagas | {stats.new} novas | "
        f"{stats.updated} já conhecidas | {stats.closed} encerradas"
    )
    return 0


def cmd_list(args, conn) -> int:
    rows = db.search_jobs(conn, limit=args.limit, **_filters(args))
    if not rows:
        print("Nenhuma vaga encontrada.")
        return 0
    for r in rows:
        status = "" if r["active"] else " [encerrada]"
        print(f"{r['title'][:44]:<44} | {r['company'][:26]:<26} | {r['location'][:22]:<22} | "
              f"{r['posted_date'] or '-':<10}{status}")
    print(f"\n{len(rows)} vaga(s) exibida(s)")
    return 0


def cmd_stats(args, conn) -> int:
    s = db.get_stats(conn)
    if s["coletas"] == 0:
        print("Banco vazio. Rode: python -m jobtracker collect")
        return 0
    print(f"Coletas realizadas : {s['coletas']} (última: {s['ultima_coleta'][0]})")
    print(f"Vagas no banco     : {s['total']} ({s['ativas']} ativas, {s['encerradas']} encerradas)")
    for source, n in s["por_fonte"].items():
        print(f"  - {source}: {n} ativas")
    print("Empresas com mais vagas ativas:")
    for company, n in s["top_empresas"]:
        print(f"  {n:>3}  {company}")
    return 0


def cmd_export(args, conn) -> int:
    rows = db.search_jobs(conn, limit=None, **_filters(args))
    if not rows:
        print("Nenhuma vaga para exportar.", file=sys.stderr)
        return 1
    try:
        out = export(rows, args.output)
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2
    print(f"{len(rows)} vagas exportadas para {out}")
    return 0


COMMANDS = {"collect": cmd_collect, "list": cmd_list, "stats": cmd_stats, "export": cmd_export}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")
    conn = db.connect(args.db)
    try:
        return COMMANDS[args.command](args, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
