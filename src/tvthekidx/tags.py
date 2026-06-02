# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import re
import sqlite3

from .database import execute_sql
from .utility import verbose, generate_oid


def tag_list(db, includeRegex=False, where=None):
    if includeRegex:
        selectSQL = "SELECT t.id, t.oid, t.tag AS tag, r.regex AS regex FROM tags t, tags_regex r WHERE t.id = r.t_id"
    else:
        selectSQL = "SELECT t.id, t.oid, t.tag AS tag FROM tags t WHERE 1 = 1"
    if where:
        selectSQL = f"{selectSQL} AND {where}"
    if includeRegex:
        selectSQL = f"{selectSQL} ORDER BY t.tag ASC, r.regex ASC"
    else:
        selectSQL = f"{selectSQL} ORDER BY t.tag ASC"
    cur = execute_sql(db, selectSQL)
    return cur.fetchall() if cur else []


def tag_add(db, tag, regex):
    tagid = regexid = None

    selectSQL = "SELECT id FROM tags WHERE tag = ?"
    cur = execute_sql(db, selectSQL, (tag, ))
    if cur:
        entry = cur.fetchone()
        if entry:
            tagid = entry[0]

    if tagid is None:
        oid = generate_oid("tag", tag)
        insertSQL = "INSERT INTO tags(tag, oid) VALUES (?, ?)"
        result = execute_sql(db, insertSQL, (tag, oid), True)
        tagid = result.lastrowid

    if tagid:
        selectSQL = "SELECT id FROM tags_regex WHERE t_id = ? AND regex = ?"
        cur = execute_sql(db, selectSQL, (tagid, regex))
        if cur:
            entry = cur.fetchone()
            if entry:
                regexid = entry[0]

    if not regexid:
        insertSQL = "INSERT INTO tags_regex(t_id, regex) VALUES (?, ?)"
        result = execute_sql(db, insertSQL, (tagid, regex), True)
        regexid = result.lastrowid

    return tagid, regexid


def tag_delete(db, tag, regex=None):
    tagid = None
    result = False

    selectSQL = "SELECT id FROM tags WHERE tag = ?"
    cur = execute_sql(db, selectSQL, (tag, ))
    if cur:
        entry = cur.fetchone()
        if entry:
            tagid = entry[0]

    if tagid:
        try:
            deleteSQL = 'DELETE FROM files_tags WHERE t_id = ?'
            result = execute_sql(db, deleteSQL, (tagid, ))

            if regex:
                deleteSQL = 'DELETE FROM tags_regex WHERE t_id = ? AND regex = ?'
                result = execute_sql(db, deleteSQL, (tagid, regex))
            else:
                deleteSQL = 'DELETE FROM tags_regex WHERE t_id = ?'
                result = execute_sql(db, deleteSQL, (tagid, ))
                deleteSQL = 'DELETE FROM tags WHERE id = ?'
                result = execute_sql(db, deleteSQL, (tagid, ), True)

            result = True
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

    return result


def tag_delete_all(db):
    execute_sql(db, "DELETE FROM files_tags")
    execute_sql(db, "DELETE FROM tags_regex")
    execute_sql(db, "DELETE FROM tags", None, True)


def tag_scanfiles(db, tag):
    if isinstance(tag, int):
        selectSQL = "SELECT t.id AS id, t.tag AS tag, r.regex AS regex FROM tags t JOIN tags_regex r ON t.id = r.t_id WHERE t.id = ?"
    else:
        selectSQL = "SELECT t.id AS id, t.tag AS tag, r.regex AS regex FROM tags t JOIN tags_regex r ON t.id = r.t_id WHERE t.tag = ?"
    regex_rows = execute_sql(db, selectSQL, (tag,)).fetchall()
    if not regex_rows:
        return

    verbose("Scanning files for tag '" + regex_rows[0]["tag"] + "'")
    execute_sql(db, "BEGIN")

    files = execute_sql(db, "SELECT id, filename FROM files").fetchall()
    insertSQL = "INSERT OR IGNORE INTO files_tags (f_id, t_id) VALUES (?, ?)"
    for r in regex_rows:
        compiled = re.compile(r["regex"])
        for f in files:
            if compiled.search(f["filename"]):
                verbose(f["filename"], 3)
                execute_sql(db, insertSQL, (f["id"], r["id"]))

    execute_sql(db, "COMMIT")


def tag_add_by_filename(db, filename):
    verbose("Checking file for tags: " + filename, 2)
    selectSQL = "SELECT t.id AS id FROM tags t JOIN tags_regex r ON t.id = r.t_id"
    cur = execute_sql(db, selectSQL)
    regex_rows = cur.fetchall()

    if not regex_rows:
        return

    insertSQL = "INSERT OR IGNORE INTO files_tags (f_id, t_id) VALUES (?, ?)"
    for row in regex_rows:
        tagid = row["id"]
        selectSQL = "SELECT id FROM files WHERE filename = ?"
        cur = execute_sql(db, selectSQL, (filename,))
        file_entry = cur.fetchone()
        if file_entry:
            f_id = file_entry[0]
            selectSQL = "SELECT regex FROM tags_regex WHERE t_id = ?"
            cur = execute_sql(db, selectSQL, (tagid, ))
            regex_rows = cur.fetchall()
            for r in regex_rows:
                compiled = re.compile(r["regex"])
                if compiled.search(filename):
                    verbose(f"File matches tag '{tagid}': " + filename, 3)
                    execute_sql(db, insertSQL, (f_id, tagid))


def getMoviesByTagid(db, tagid, whereSql=None, params=None):
    selectSQL = "SELECT m.id AS id, m.oid AS oid, m.title AS title FROM movies m, files f, files_tags ft WHERE ft.t_id=? AND ft.f_id=f.id AND f.movie_id=m.id"
    if whereSql:
        selectSQL = f"{selectSQL} AND {whereSql}"
    selectSQL = f"{selectSQL} ORDER BY m.year ASC, m.title ASC"
    all_params = [tagid] + ([*params] if params else [])
    cur = execute_sql(db, selectSQL, all_params)
    return cur.fetchall() if cur else []


def list(db):
    result = tag_list(db, True)
    if not result:
        print("No tags found")
        return

    max_tag = max(len(row["tag"]) for row in result)
    max_regex = max(len(row["regex"]) for row in result)

    for i, row in enumerate(result, start=1):
        print(f"| {i:3} | {row['tag']:<{max_tag}} | {row['regex']:<{max_regex}} | ")


def add(db, tag, regex):
    tagid, regexid = tag_add(db, tag, regex)
    if tagid:
        tag_scanfiles(db, tagid)


def delete(db, tag, regex=None):
    tag_delete(db, tag, regex)


def delete_all(db):
    tag_delete_all(db)


def export(db, dbfile):
    result = tag_list(db, True)
    if not result:
        return
    for row in result:
        print(f'tvthekidx tags -d "{dbfile}" -a add -t "{row["tag"]}" -r "{row["regex"]}"')
