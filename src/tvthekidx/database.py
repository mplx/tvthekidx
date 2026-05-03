# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

from . import online
from . utility import verbose, normalize_string, generate_oid

import sqlite3
from sqlite3 import Error

import os
import re


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA cache_size = -65536")    # 64 MB page cache
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA mmap_size = 268435456")  # 256 MB memory-mapped I/O
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

        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM movies")
        rows = cursor.fetchall()
        for row in rows:
            row_id, title = row
            normalized = normalize_string(title if title else "")
            cursor.execute("UPDATE movies SET title_normalized = ? WHERE id = ?", (normalized, row_id))
        conn.commit()
        cursor.close()

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " tvstation, lastseen, uuid "
    if DBVERSION == 5:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, "ALTER TABLE files ADD COLUMN tvstation TEXT DEFAULT NULL", None, True)
        execute_sql(conn, "ALTER TABLE files ADD COLUMN lastseen INTEGER DEFAULT NULL", None, True)
        execute_sql(conn, "UPDATE files SET lastseen = cast(strftime('%s','now') as int)", None, True)
        execute_sql(conn, "ALTER TABLE movies ADD COLUMN oid TEXT DEFAULT NULL", None, True)
        execute_sql(conn, "ALTER TABLE files  ADD COLUMN oid TEXT DEFAULT NULL", None, True)
        execute_sql(conn, "ALTER TABLE actors ADD COLUMN oid TEXT DEFAULT NULL", None, True)
        execute_sql(conn, "ALTER TABLE tags   ADD COLUMN oid TEXT DEFAULT NULL", None, True)

        cursor = conn.cursor()
        cursor.execute("SELECT id, tmdb_id, title, year FROM movies")
        movies_updates = [(generate_oid("movie", str(r[1]) if r[1] else f"{r[2]}:{r[3]}"), r[0]) for r in cursor.fetchall()]
        cursor.executemany("UPDATE movies SET oid = ? WHERE id = ?", movies_updates)

        cursor.execute("SELECT id, collection, relpath, filename FROM files")
        files_updates = [(generate_oid("file", f"{r[1]}:{r[2]}:{r[3]}"), r[0]) for r in cursor.fetchall()]
        cursor.executemany("UPDATE files SET oid = ? WHERE id = ?", files_updates)

        cursor.execute("SELECT id, tmdb_id FROM actors")
        actors_updates = [(generate_oid("actor", str(r[1])), r[0]) for r in cursor.fetchall()]
        cursor.executemany("UPDATE actors SET oid = ? WHERE id = ?", actors_updates)

        cursor.execute("SELECT id, tag FROM tags")
        tags_updates = [(generate_oid("tag", r[1]), r[0]) for r in cursor.fetchall()]
        cursor.executemany("UPDATE tags SET oid = ? WHERE id = ?", tags_updates)
        conn.commit()

        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_movies" ON "movies" ("oid")', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_files"  ON "files"  ("oid")', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_actors" ON "actors" ("oid")', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_tags"   ON "tags"   ("oid")', None, True)
        cursor.close()

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " files_attachments table, poster/profile migration "
    if DBVERSION == 6:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, 'CREATE TABLE "files_attachments" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "type" TEXT NOT NULL, "data" BLOB)', None, True)
        execute_sql(conn, 'CREATE TABLE "files_attachments_map" ("f_id" INTEGER NOT NULL, "a_id" INTEGER NOT NULL, PRIMARY KEY("f_id","a_id"), FOREIGN KEY("f_id") REFERENCES "files"("id"), FOREIGN KEY("a_id") REFERENCES "files_attachments"("id"))', None, True)
        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)
        cursor = conn.cursor()
        cursor.execute("SELECT id, screenshot FROM files WHERE screenshot IS NOT NULL")
        for row in cursor.fetchall():
            cursor2 = conn.cursor()
            cursor2.execute("INSERT INTO files_attachments (type, data) VALUES ('screenshot', ?)", (row[1],))
            att_id = cursor2.lastrowid
            cursor2.execute("INSERT INTO files_attachments_map (f_id, a_id) VALUES (?, ?)", (row[0], att_id))
        conn.commit()
        cursor.close()
        execute_sql(conn, "ALTER TABLE files DROP COLUMN screenshot", None, True)

        execute_sql(conn, "ALTER TABLE files_attachments ADD COLUMN ref_id INTEGER DEFAULT NULL", None, True)
        cursor = conn.cursor()
        cursor.execute("SELECT id, poster FROM movies WHERE poster IS NOT NULL")
        for row in cursor.fetchall():
            cursor.execute("INSERT INTO files_attachments (type, data, ref_id) VALUES ('poster', ?, ?)", (row[1], row[0]))
        cursor.execute("SELECT id, profile FROM actors WHERE profile IS NOT NULL")
        for row in cursor.fetchall():
            cursor.execute("INSERT INTO files_attachments (type, data, ref_id) VALUES ('profile', ?, ?)", (row[1], row[0]))
        conn.commit()
        cursor.close()
        execute_sql(conn, "ALTER TABLE movies DROP COLUMN poster", None, True)
        execute_sql(conn, "ALTER TABLE actors DROP COLUMN profile", None, True)

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " drop files_attachments_map, migrate screenshots to ref_id, rename files_attachments to attachments, composite index "
    if DBVERSION == 7:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, "UPDATE files_attachments SET ref_id = (SELECT f_id FROM files_attachments_map WHERE a_id = files_attachments.id) WHERE type = 'screenshot'", None, True)
        execute_sql(conn, 'DROP TABLE "files_attachments_map"', None, True)
        execute_sql(conn, 'ALTER TABLE "files_attachments" RENAME TO "attachments"', None, True)
        execute_sql(conn, 'CREATE INDEX "idx_attachments_ref_type" ON "attachments" ("ref_id", "type")', None, True)

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " up-to-date "
    if DBVERSION == 8:
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
    selectSQL = "SELECT DISTINCT id, collection, filename, size, added, ctime, codec, width, height, duration, tvstation FROM files WHERE movie_id = ? ORDER BY collection ASC"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getCollections_bulk(db, movie_ids):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT DISTINCT id, collection, filename, size, added, ctime, codec, width, height, duration, tvstation, movie_id FROM files WHERE movie_id IN ({ph}) ORDER BY collection ASC",
        list(movie_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["movie_id"], []).append(row)
    return result


def getCast_bulk(db, movie_ids, limit=None):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT a.*, c.m_id FROM actors_movies c JOIN actors a ON c.a_id = a.id WHERE c.m_id IN ({ph}) ORDER BY a.popularity DESC",
        list(movie_ids))
    result = {}
    for row in cur.fetchall():
        lst = result.setdefault(row["m_id"], [])
        if limit is None or len(lst) < limit:
            lst.append(row)
    return result


def getCrew_bulk(db, movie_ids, where=None, limit=None):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    sql = f"SELECT a.*, c.job, c.m_id FROM crew_movies c JOIN actors a ON c.a_id = a.id WHERE c.m_id IN ({ph})"
    if where:
        sql += f" AND ({where})"
    sql += " ORDER BY a.popularity DESC"
    cur = db.cursor()
    cur.execute(sql, list(movie_ids))
    result = {}
    for row in cur.fetchall():
        lst = result.setdefault(row["m_id"], [])
        if limit is None or len(lst) < limit:
            lst.append(row)
    return result


def get_file_id(db, collection, filename, relpath):
    cur = db.cursor()
    cur.execute("SELECT id FROM files WHERE collection = ? AND filename = ? AND relpath = ?", (collection, filename, relpath))
    row = cur.fetchone()
    return row["id"] if row else None


def add_file_attachment(db, file_id, att_type, data):
    cur = db.cursor()
    cur.execute("INSERT INTO attachments (type, data, ref_id) VALUES (?, ?, ?)",
                (att_type, sqlite3.Binary(data), file_id))
    db.commit()


def count_file_attachments(db, file_id, att_type=None):
    cur = db.cursor()
    sql = "SELECT COUNT(*) FROM attachments WHERE ref_id = ?"
    params = (file_id,)
    if att_type:
        sql += " AND type = ?"
        params = (file_id, att_type)
    cur.execute(sql, params)
    return cur.fetchone()[0]


def get_file_attachments(db, file_id, att_type=None):
    cur = db.cursor()
    sql = "SELECT id, type, data FROM attachments WHERE ref_id = ?"
    params = (file_id,)
    if att_type:
        sql += " AND type = ?"
        params = (file_id, att_type)
    cur.execute(sql, params)
    return cur.fetchall()


def get_file_attachments_bulk(db, file_ids, att_type=None):
    if not file_ids:
        return {}
    ph = ",".join("?" * len(file_ids))
    sql = f"SELECT id, type, data, ref_id FROM attachments WHERE ref_id IN ({ph})"
    params = list(file_ids)
    if att_type:
        sql += " AND type = ?"
        params.append(att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["ref_id"], []).append(row)
    return result


def delete_file_attachments(db, file_id, att_type=None):
    cur = db.cursor()
    if att_type:
        cur.execute("DELETE FROM attachments WHERE ref_id = ? AND type = ?", (file_id, att_type))
    else:
        cur.execute("DELETE FROM attachments WHERE ref_id = ?", (file_id,))
    db.commit()


def clear_screenshots(db):
    cur = db.cursor()
    cur.execute("DELETE FROM attachments WHERE type = 'screenshot'")
    db.commit()


def add_movie_attachment(db, movie_id, att_type, data):
    cur = db.cursor()
    cur.execute("INSERT INTO attachments (type, data, ref_id) VALUES (?, ?, ?)", (att_type, sqlite3.Binary(data), movie_id))
    db.commit()


def get_movie_attachments(db, movie_id, att_type=None):
    sql = "SELECT id, type, data FROM attachments WHERE ref_id = ?"
    params = (movie_id,)
    if att_type:
        sql += " AND type = ?"
        params = (movie_id, att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def get_movie_attachments_bulk(db, movie_ids, att_type=None):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    sql = f"SELECT id, type, data, ref_id FROM attachments WHERE ref_id IN ({ph})"
    params = list(movie_ids)
    if att_type:
        sql += " AND type = ?"
        params.append(att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["ref_id"], []).append(row)
    return result


def add_actor_attachment(db, actor_id, att_type, data):
    cur = db.cursor()
    cur.execute("INSERT INTO attachments (type, data, ref_id) VALUES (?, ?, ?)", (att_type, sqlite3.Binary(data), actor_id))
    db.commit()


def get_actor_attachments(db, actor_id, att_type=None):
    sql = "SELECT id, type, data FROM attachments WHERE ref_id = ?"
    params = (actor_id,)
    if att_type:
        sql += " AND type = ?"
        params = (actor_id, att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def get_actor_attachments_bulk(db, actor_ids, att_type=None):
    if not actor_ids:
        return {}
    ph = ",".join("?" * len(actor_ids))
    sql = f"SELECT id, type, data, ref_id FROM attachments WHERE ref_id IN ({ph})"
    params = list(actor_ids)
    if att_type:
        sql += " AND type = ?"
        params.append(att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["ref_id"], []).append(row)
    return result


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
    selectSQL = "SELECT m.id, m.oid, m.title, m.title_normalized, m.score, m.year FROM actors_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ?"
    selectSQL += " UNION "
    selectSQL += "SELECT m.id, m.oid, m.title, m.title_normalized, m.score, m.year FROM crew_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ?"
    selectSQL += "ORDER BY m.title_normalized COLLATE NOCASE ASC, m.year ASC"
    cur.execute(selectSQL, (aid, aid))
    return cur.fetchall()


def getMoviesByActor_bulk(db, actor_ids):
    if not actor_ids:
        return {}
    ph = ",".join("?" * len(actor_ids))
    params = list(actor_ids)
    sql = (
        f"SELECT m.id, m.oid, m.title, m.title_normalized, m.score, m.year, c.a_id "
        f"FROM actors_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id IN ({ph}) "
        f"UNION "
        f"SELECT m.id, m.oid, m.title, m.title_normalized, m.score, m.year, c.a_id "
        f"FROM crew_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id IN ({ph}) "
        f"ORDER BY m.title_normalized COLLATE NOCASE ASC, m.year ASC"
    )
    cur = db.cursor()
    cur.execute(sql, params + params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["a_id"], []).append(row)
    return result


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
    oid = generate_oid("file", f"{collection}:{relpath}:{filename}")
    insertSQL = "INSERT INTO files (collection, filename, relpath, movie_id, lastseen, oid) VALUES (?, ?, ?, NULL, cast(strftime('%s','now') as int), ?)"
    selectSQL = "SELECT * FROM files WHERE collection = ? AND filename = ? AND relpath = ?"
    cur = execute_sql(db, selectSQL, (collection, filename, relpath))
    entry = cur.fetchone()
    if entry is None:
        execute_sql(db, insertSQL, (collection, filename, relpath, oid))
        return True
    return entry


def updateLastSeen(db, collection, filename, relpath):
    execute_sql(db, "UPDATE files SET lastseen = cast(strftime('%s','now') as int) WHERE collection = ? AND filename = ? AND relpath = ?", (collection, filename, relpath))


def addMovieToDb(db, movie):
    key = str(movie['tmdb_id']) if movie['tmdb_id'] else f"{movie['title']}:{movie['release_year']}"
    oid = generate_oid("movie", key)
    insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, title_normalized, year, description, popularity, score, oid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    result = execute_sql(db, insertSQL, (movie['tmdb_id'], movie['title'], movie['orig_title'], normalize_string(movie['title']), movie['release_year'], movie['description'], movie['popularity'], movie['score'], oid))
    movie_id = result.lastrowid
    if movie.get('poster'):
        add_movie_attachment(db, movie_id, 'poster', movie['poster'])
    return movie_id


def addActorToDb(db, actor):
    selectSQL = "SELECT id FROM actors WHERE tmdb_id = ?"

    cur = execute_sql(db, selectSQL, (actor['tmdb_id'], ))
    entry = cur.fetchone()

    if entry is None:
        oid = generate_oid("actor", str(actor['tmdb_id']))
        insertSQL = "INSERT INTO actors(name, popularity, tmdb_id, oid) VALUES (?, ?, ?, ?)"
        result = execute_sql(db, insertSQL, (actor['name'], actor['popularity'], actor['tmdb_id'], oid))
        actor_id = result.lastrowid
        if actor.get('profile'):
            add_actor_attachment(db, actor_id, 'profile', actor['profile'])
        return actor_id

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


