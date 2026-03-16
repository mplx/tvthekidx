# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2025 developer@mplx.eu

from . import online
from . utility import verbose, normalize_string

import sqlite3
from sqlite3 import Error

import os
import re


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
    except BaseException as e:
        print(e)
    else:
        return conn


def execute_sql(conn, sql, param=None, doCommit=False):
    if param is None:
        param = []

    try:
        c = conn.cursor()
        c.execute(sql, param)
        if doCommit:
            conn.commit()
        return c
    except Error as e:
        print(e)


def cleanup_db(db):
    verbose("Database cleanup...", 2)

    verbose("Removing duplicate movies...", 3)
    SQL = "SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING COUNT(*)>1 ORDER BY tmdb_id"
    cur = execute_sql(db, SQL)
    entries = cur.fetchall()
    for e in entries:
        tmdbid = e['tmdb_id']
        SQL = "SELECT id FROM movies WHERE tmdb_id = ?"
        cur = execute_sql(db, SQL, (tmdbid, ))
        entry = cur.fetchone()
        master = entry['id']
        obsolete = cur.fetchall()
        for o in obsolete:
            actorsUpdateSQL = "UPDATE actors_movies SET m_id = ? WHERE m_id = ?"
            actorsDeleteSQL = "DELETE FROM actors_movies WHERE m_id = ?"
            crewDeleteSQL = "DELETE FROM crew_movies WHERE m_id = ?"
            filesUpdateSQL = "UPDATE files SET movie_id = ? WHERE movie_id = ?"
            cleanupSQL = "DELETE FROM movies WHERE id = ?"
            try:
                c = db.cursor()
                c.execute(actorsUpdateSQL, (master, o['id']))
            except Error:
                cur = execute_sql(db, actorsDeleteSQL, (o['id'], ))
                cur = execute_sql(db, crewDeleteSQL, (o['id'], ))
            cur = execute_sql(db, filesUpdateSQL, (master, o['id']))
            cur = execute_sql(db, cleanupSQL, (o['id'], ))

    verbose("Optimizing database...", 2)
    db.commit()
    SQL = "VACUUM"
    execute_sql(db, SQL)

    return True


def initialize_db(db_file):
    createMode = not os.path.isfile(db_file)

    if createMode:
        verbose("Creating database...", 2)
        conn = create_connection(db_file)

        verbose("Creating table movies...", 3)
        SQL = 'CREATE TABLE "movies" ("id" INTEGER NOT NULL, "title" TEXT NOT NULL, "title_orig" TEXT NOT NULL, "year" INTEGER NOT NULL, "description" TEXT, "popularity" REAL DEFAULT 0, "score" REAL DEFAULT 0, "poster" BLOB, "tmdb_id" INTEGER, PRIMARY KEY("id" AUTOINCREMENT) )'
        execute_sql(conn, SQL)

        verbose("Creating table files...", 3)
        SQL = 'CREATE TABLE "files" ("id" INTEGER, "collection" TEXT DEFAULT NULL, "filename" TEXT NOT NULL, "relpath" TEXT DEFAULT NULL, "size" INTEGER DEFAULT NULL, "ctime" INTEGER DEFAULT NULL, "mtime" INTEGER DEFAULT NULL, "movie_id" INTEGER, "added" INTEGER default (cast(strftime(\'%s\',\'now\') as int)), "lastmod" INTEGER default (cast(strftime(\'%s\',\'now\') as int)), PRIMARY KEY("id" AUTOINCREMENT), FOREIGN KEY("movie_id") REFERENCES"movies"("id"))'
        execute_sql(conn, SQL)

        verbose("Creating table actors...", 3)
        SQL = 'CREATE TABLE "actors" ("id" INTEGER, "name" TEXT NOT NULL, "popularity" REAL, "profile" BLOB, "tmdb_id" INTEGER NOT NULL UNIQUE, PRIMARY KEY("id" AUTOINCREMENT))'
        execute_sql(conn, SQL)

        verbose("Creating table actors/movies...", 3)
        SQL = 'CREATE TABLE "actors_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, FOREIGN KEY("m_id") REFERENCES "movies"("id"), FOREIGN KEY("a_id") REFERENCES "actors"("id"), PRIMARY KEY("a_id","m_id"))'
        execute_sql(conn, SQL)

        verbose("Creating table indices...", 3)
        SQL = 'CREATE UNIQUE INDEX "unique_fn" ON "files" ("collection" ASC, "filename" ASC, "relpath" ASC)'
        execute_sql(conn, SQL)

    else:
        verbose("Connecting database...", 2)
        conn = create_connection(db_file)

    upgrade_db(db_file)

    SQL = "PRAGMA foreign_keys = ON"
    execute_sql(conn, SQL)

    return conn


def upgrade_db(db_file):
    verbose("Opening database...", 3)
    conn = create_connection(db_file)

    verbose("Getting database version...", 3)
    SQL = "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
    cur = execute_sql(conn, SQL)
    sysval = cur.fetchone()
    if sysval is None:
        verbose("Creating settings table...", 3)
        SQL = 'CREATE TABLE "settings" ("dbkey" TEXT, "value_int" INTEGER, "value_str" TEXT, PRIMARY KEY("dbkey"))'
        execute_sql(conn, SQL, None, True)
        SQL = 'INSERT INTO "settings" ("dbkey", "value_int", "value_str") VALUES ("dbversion", 1, NULL)'
        execute_sql(conn, SQL)
        conn.commit()
    SQL = "SELECT value_int FROM settings WHERE dbkey='dbversion'"
    cur = execute_sql(conn, SQL)
    DBVERSION = cur.fetchone()[0]
    verbose("Database version " + str(DBVERSION) + " found", 2)

    " ffmpeg probe "
    if DBVERSION == 1:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)
        SQL = 'ALTER TABLE files ADD COLUMN width INTEGER'
        execute_sql(conn, SQL, None, True)
        SQL = 'ALTER TABLE files ADD COLUMN height INTEGER'
        execute_sql(conn, SQL, None, True)
        SQL = 'ALTER TABLE files ADD COLUMN duration REAL'
        execute_sql(conn, SQL, None, True)
        SQL = 'ALTER TABLE files ADD COLUMN codec TEXT'
        execute_sql(conn, SQL, None, True)
        SQL = 'ALTER TABLE files ADD COLUMN screenshot BLOB'
        execute_sql(conn, SQL, None, True)
        SQL = f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'"
        execute_sql(conn, SQL, None, True)

    " crew "
    if DBVERSION == 2:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)
        SQL = 'CREATE TABLE "crew_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, "job" TEXT, FOREIGN KEY("m_id") REFERENCES "movies"("id"), FOREIGN KEY("a_id") REFERENCES "actors"("id"), PRIMARY KEY("a_id","m_id"))'
        execute_sql(conn, SQL, None, True)
        SQL = f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'"
        execute_sql(conn, SQL, None, True)

    " tags "
    if DBVERSION == 3:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)
        SQL = 'CREATE TABLE "tags" ("id" INTEGER, "tag" TEXT NOT NULL UNIQUE, PRIMARY KEY("id" AUTOINCREMENT))'
        execute_sql(conn, SQL, None, True)
        SQL = 'CREATE TABLE "files_tags" ("f_id" INTEGER, "t_id" INTEGER, PRIMARY KEY("f_id","t_id"), FOREIGN KEY("t_id") REFERENCES "tags"("id"), FOREIGN KEY("f_id") REFERENCES "files"("id"))'
        execute_sql(conn, SQL, None, True)
        SQL = 'CREATE TABLE "tags_regex" ("id" INTEGER, "t_id" INTEGER, "regex" TEXT, FOREIGN KEY("t_id") REFERENCES "tags"("id"), PRIMARY KEY("id"))'
        execute_sql(conn, SQL, None, True)
        SQL = f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'"
        execute_sql(conn, SQL, None, True)

    " title normalization "
    if DBVERSION == 4:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        SQL = "ALTER TABLE movies ADD COLUMN title_normalized TEXT"
        execute_sql(conn, SQL, None, True)

        SQL = f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'"
        execute_sql(conn, SQL, None, True)

        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM movies")
        rows = cursor.fetchall()
        for row in rows:
            row_id, title = row
            normalized = normalize_string(title if title else "")
            cursor.execute("UPDATE movies SET title_normalized = ? WHERE id = ?", (normalized, row_id))
        conn.commit()
        cursor.close()

    " up-to-date "
    if DBVERSION == 5:
        verbose("Database up-to-date", 1)


def getMovies(db, where=None, orderby=None, limit=None):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT m.* FROM movies m JOIN files f ON m.id=f.movie_id"
    if where:
        selectSQL = f"{selectSQL} WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL)
    return cur.fetchall()


def getCast(db, mid, limit=None):
    cur = db.cursor()
    selectSQL = "SELECT a.* FROM actors_movies c JOIN actors a ON c.a_id = a.id JOIN movies m ON c.m_id = m.id WHERE m.id = ? ORDER BY a.popularity DESC"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getCrew(db, mid, where=None, limit=None):
    cur = db.cursor()
    selectSQL = "SELECT a.*, c.job FROM crew_movies c JOIN actors a ON c.a_id = a.id JOIN movies m ON c.m_id = m.id WHERE (m.id = ?)"
    if where:
        selectSQL = f"{selectSQL} AND ({where})"
    selectSQL = selectSQL + "ORDER BY a.popularity DESC"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getCollections(db, mid):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT id, collection, filename, size, added, ctime, codec, width, height, duration, screenshot FROM files WHERE movie_id = ? ORDER BY collection ASC"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getActors(db, where=None, orderby="popularity DESC, name ASC"):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT a.* FROM actors a"
    if where:
        selectSQL = f"{selectSQL} JOIN actors_movies am ON am.a_id=a.id JOIN movies m ON am.m_id=m.id JOIN files f ON f.movie_id = m.id WHERE {where}"
        selectSQL = f"{selectSQL} UNION SELECT DISTINCT a.* FROM actors a"
        selectSQL = f"{selectSQL} JOIN crew_movies cm ON cm.a_id=a.id JOIN movies m ON cm.m_id=m.id JOIN files f ON f.movie_id = m.id WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    cur.execute(selectSQL)
    return cur.fetchall()


def getMoviesByActor(db, aid):
    cur = db.cursor()
    selectSQL = "SELECT m.id, m.title, m.title_normalized, m.score, m.year FROM actors_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ?"
    selectSQL += " UNION "
    selectSQL += "SELECT m.id, m.title, m.title_normalized, m.score, m.year FROM crew_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ?"
    selectSQL += "ORDER BY m.title_normalized COLLATE NOCASE ASC, m.year ASC"
    cur.execute(selectSQL, (aid, aid))
    return cur.fetchall()


def assignMovieToFile(db, fid, mid):
    cur = db.cursor()
    updateSQL = "UPDATE files SET movie_id = ? WHERE id = ?"
    cur.execute(updateSQL, (mid, fid))
    return True


def scanMovies(db, search):
    selectSQL = "SELECT id, filename FROM files WHERE (movie_id IS NULL or movie_id=0) ORDER BY filename ASC"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        m = re.search(r'(.*) \(([0-9][0-9][0-9][0-9])\).+', row['filename'])
        basename = m.group(1)
        year = int(m.group(2))
        m_id = lookupMovie(db, search, basename, year)
        assignMovieToFile(db, row['id'], m_id)
        db.commit()
    return None


def addFileToDb(db, collection, filename, relpath):
    insertSQL = "INSERT INTO files (collection, filename, relpath, movie_id) VALUES (?, ?, ?, NULL)"
    selectSQL = "SELECT * FROM files WHERE collection = ? AND filename = ? AND relpath = ?"
    cur = execute_sql(db, selectSQL, (collection, filename, relpath))
    entry = cur.fetchone()
    if entry is None:
        execute_sql(db, insertSQL, (collection, filename, relpath))
        return True
    return entry


def addMovieToDb(db, movie):
    insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, title_normalized, year, description, popularity, score, poster) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    result = execute_sql(db, insertSQL, (movie['tmdb_id'], movie['title'], movie['orig_title'], normalize_string(movie['title']), movie['release_year'], movie['description'], movie['popularity'], movie['score'], movie['poster']))
    return result.lastrowid


def addActorToDb(db, actor):
    selectSQL = "SELECT id FROM actors WHERE tmdb_id = ?"

    cur = execute_sql(db, selectSQL, (actor['tmdb_id'], ))
    entry = cur.fetchone()

    if entry is None:
        insertSQL = "INSERT INTO actors(name, popularity, profile, tmdb_id) VALUES (?, ?, ?, ?)"
        result = execute_sql(db, insertSQL, (actor['name'], actor['popularity'], actor['profile'], actor['tmdb_id']))
        return result.lastrowid

    return entry['id']


def addActorToMovieDb(db, mid, aid):
    selectSQL = "SELECT * FROM actors_movies WHERE a_id = ? AND m_id = ?"

    cur = execute_sql(db, selectSQL, (aid, mid, ))
    entry = cur.fetchone()

    if entry is None:
        insertSQL = "INSERT INTO actors_movies(a_id, m_id) VALUES (?, ?)"
        execute_sql(db, insertSQL, (aid, mid))

    return True


def addCrewToMovieDb(db, mid, aid, job):
    selectSQL = "SELECT * FROM crew_movies WHERE a_id = ? AND m_id = ?"

    cur = execute_sql(db, selectSQL, (aid, mid, ))
    entry = cur.fetchone()

    if entry is None:
        insertSQL = "INSERT INTO crew_movies(a_id, m_id, job) VALUES (?, ?, ?)"
        execute_sql(db, insertSQL, (aid, mid, job))

    return True


def scanCredits(db, movie):
    verbose("Scanning for cast and crew...", 2)
    selectSQL = "SELECT id, title, tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND NOT (id IN (SELECT DISTINCT m_id FROM actors_movies UNION SELECT DISTINCT m_id FROM crew_movies)) ORDER BY title ASC"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        verbose("Lookup cast for " + row['title'], 2)
        cast, crew = online.query_cast(movie, row['tmdb_id'])
        for person in cast:
            aid = addActorToDb(db, person)
            addActorToMovieDb(db, row['id'], aid)
        for person in crew:
            aid = addActorToDb(db, person)
            addCrewToMovieDb(db, row['id'], aid, person['job'])
        db.commit()
    return None


def lookupMovie(db, search, title, year):
    verbose("Lookup movie: " + title, 2)
    cur = db.cursor()
    selectSQL = "SELECT id FROM movies WHERE title=? AND year=?"
    cur = execute_sql(db, selectSQL, (title, year))
    entry = cur.fetchone()
    if entry is None:
        result = online.query_movie(search, title, year)
        if result is not None:
            movie = {
                "tmdb_id": result['id'],
                "title": result['title'],
                "orig_title": result['original_title'],
                "release_year": result['release_date'][0:4],
                "description": result['overview'] if result['overview'] else None,
                "popularity": result['popularity'],  # https://developers.themoviedb.org/3/getting-started/popularity
                "score": result['vote_average'] * 10,
                "poster": online.fetchPoster(result['poster_path'])
            }
            return addMovieToDb(db, movie)
        else:
            verbose("Cannot find online: " + title, 1)
            unknown = {
                "tmdb_id": None,
                "title": title,
                "orig_title": title,
                "release_year": year,
                "description": None,
                "popularity": "0",
                "score": "0",
                "poster": None,
            }
            return addMovieToDb(db, unknown)
    else:
        return entry['id']


def store_screenshot(db, collection, m, filename, relpath, time=500):
    try:
        from . import files
        screenshot = files.get_screenshot(m, time)
        updateSQL = "UPDATE files SET screenshot = ? WHERE collection = ? AND filename = ? AND relpath = ?"
        execute_sql(db, updateSQL, (sqlite3.Binary(screenshot), collection, filename, relpath))
        return True
    except:
        return False


def tag_list(db, includeRegex=False, where=None):
    if includeRegex:
        selectSQL = "SELECT t.id, t.tag AS tag, r.regex AS regex FROM tags t, tags_regex r WHERE t.id = r.t_id"
    else:
        selectSQL = "SELECT t.id, t.tag AS tag FROM tags t WHERE 1 = 1"
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
        insertSQL = "INSERT INTO tags(tag) VALUES (?)"
        result = execute_sql(db, insertSQL, (tag, ), True)
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


def tag_delete(db, tag, regex = None):
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


def tag_scanfiles(db, tag):
    if isinstance(tag, int):
        selectSQL = "SELECT t.id AS id, t.tag AS tag, r.regex AS regex FROM tags t JOIN tags_regex r ON t.id = r.t_id WHERE t.id = ?"
    else:
        selectSQL = "SELECT t.id AS id, t.tag AS tag, r.regex AS regex FROM tags t JOIN tags_regex r ON t.id = r.t_id WHERE t.tag = ?"
    regex_rows = list(execute_sql(db, selectSQL, (tag,)))
    if not regex_rows:
        return

    verbose("Scanning files for tag '" + regex_rows[0]["tag"] + "'")
    execute_sql(db, "BEGIN")

    files = list(execute_sql(db, "SELECT id, filename FROM files"))
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


def getMoviesByTagid(db, tagid, whereSql):
    selectSQL = "SELECT m.id AS id, m.title AS title FROM movies m, files f, files_tags ft WHERE ft.t_id=? AND ft.f_id=f.id AND f.movie_id=m.id"
    if whereSql:
        selectSQL = f"{selectSQL} AND {whereSql}"
    selectSQL = f"{selectSQL}ORDER BY m.year ASC, m.title ASC"
    return list(execute_sql(db, selectSQL, (tagid,)))


def tag_delete_all(db):
    execute_sql(db, "DELETE FROM files_tags")
    execute_sql(db, "DELETE FROM tags_regex")
    execute_sql(db, "DELETE FROM tags", None, True)


def regex_count(db, regex, tag = None):
    return 0
