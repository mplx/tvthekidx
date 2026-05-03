# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import argparse
import sys


def parse_args(remaining):
    parser = argparse.ArgumentParser(prog="tvthekidx export --format text", add_help=False)
    parser.add_argument("--output", "-o", dest="outputFile", default=None, help="output file (default: stdout)")
    plugin_args, _ = parser.parse_known_args(remaining)
    return plugin_args


def export(db, collection, args, plugin_args):
    whereSql = ""
    if collection:
        whereSql = "("
        for col in collection:
            whereSql += f"(collection='{col}') OR "
        whereSql = whereSql[:-4] + ")"

    cur = db.cursor()
    selectSQL = (
        "SELECT DISTINCT m.title, m.year, f.tvstation "
        "FROM movies m JOIN files f ON m.id = f.movie_id"
    )
    if whereSql:
        selectSQL += f" WHERE {whereSql}"
    selectSQL += " ORDER BY m.title_normalized COLLATE NOCASE ASC, m.year ASC"
    cur.execute(selectSQL)
    rows = cur.fetchall()

    lines = []
    for r in rows:
        tv = r['tvstation']
        bracket = f" [{tv.upper()}]" if tv else ""
        lines.append(f"{r['title']} ({r['year']}){bracket}")

    if plugin_args.outputFile:
        with open(plugin_args.outputFile, "w", encoding="utf8") as f:
            f.write("\n".join(lines) + "\n")
    else:
        sys.stdout.write("\n".join(lines) + "\n")
