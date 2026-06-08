# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import os

from .database import create_connection, execute_sql
from .utility import verbose, normalize_string, generate_oid


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

    " genres, error counters "
    if DBVERSION == 8:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, 'CREATE TABLE "genres" ("id" INTEGER NOT NULL, "tmdb_id" INTEGER NOT NULL UNIQUE, "name" TEXT NOT NULL, "oid" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))', None, True)
        execute_sql(conn, 'CREATE TABLE "movies_genres" ("movie_id" INTEGER NOT NULL, "genre_id" INTEGER NOT NULL, PRIMARY KEY("movie_id","genre_id"), FOREIGN KEY("movie_id") REFERENCES "movies"("id"), FOREIGN KEY("genre_id") REFERENCES "genres"("id"))', None, True)
        execute_sql(conn, "ALTER TABLE movies ADD COLUMN cast_error_count INTEGER DEFAULT 0", None, True)
        execute_sql(conn, "ALTER TABLE movies ADD COLUMN genre_error_count INTEGER DEFAULT 0", None, True)
        execute_sql(conn, "ALTER TABLE movies ADD COLUMN refresh_timestamp INTEGER DEFAULT NULL", None, True)
        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " collections table, collection_id FK, drop collection text column "
    if DBVERSION == 9:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, 'CREATE TABLE "collections" ("id" INTEGER NOT NULL, "guid" TEXT NOT NULL UNIQUE, "name" TEXT NOT NULL UNIQUE, "movie_filename_regex" TEXT DEFAULT NULL, "tvshow_filename_regex" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))', None, True)

        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT collection FROM files WHERE collection IS NOT NULL")
        for row in cursor.fetchall():
            name = row[0]
            guid = generate_oid("collection", name)
            cursor.execute("INSERT INTO collections (guid, name) VALUES (?, ?)", (guid, name))
        conn.commit()
        cursor.close()

        execute_sql(conn, "ALTER TABLE files ADD COLUMN collection_id INTEGER REFERENCES collections(id)", None, True)
        execute_sql(conn, "UPDATE files SET collection_id = (SELECT id FROM collections WHERE name = files.collection)", None, True)
        execute_sql(conn, 'DROP INDEX IF EXISTS "unique_fn"', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "unique_fn" ON "files" ("collection_id", "filename", "relpath")', None, True)
        execute_sql(conn, "ALTER TABLE files DROP COLUMN collection", None, True)

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " tvshows, seasons, episodes, TV junction tables, files.episode_id, files.libtype "
    if DBVERSION == 10:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, '''CREATE TABLE "tvshows" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "title" TEXT NOT NULL,
            "title_orig" TEXT NOT NULL,
            "title_normalized" TEXT,
            "year" INTEGER NOT NULL,
            "description" TEXT,
            "popularity" REAL DEFAULT 0,
            "score" REAL DEFAULT 0,
            "tmdb_id" INTEGER,
            "oid" TEXT,
            "cast_error_count" INTEGER DEFAULT 0,
            "genre_error_count" INTEGER DEFAULT 0,
            "season_error_count" INTEGER DEFAULT 0,
            "refresh_timestamp" INTEGER DEFAULT NULL
        )''', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_tvshows" ON tvshows (oid)', None, True)

        execute_sql(conn, '''CREATE TABLE "seasons" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "season_number" INTEGER NOT NULL,
            "title" TEXT,
            "year" INTEGER,
            "oid" TEXT,
            UNIQUE(tvshow_id, season_number)
        )''', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_seasons" ON seasons (oid)', None, True)

        execute_sql(conn, '''CREATE TABLE "episodes" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "season_id" INTEGER NOT NULL REFERENCES seasons(id),
            "season_number" INTEGER NOT NULL,
            "episode_number" INTEGER NOT NULL,
            "title" TEXT,
            "year" INTEGER,
            "description" TEXT,
            "score" REAL DEFAULT 0,
            "oid" TEXT,
            UNIQUE(tvshow_id, season_number, episode_number)
        )''', None, True)
        execute_sql(conn, 'CREATE UNIQUE INDEX "oid_episodes" ON episodes (oid)', None, True)

        execute_sql(conn, '''CREATE TABLE "actors_tvshows" (
            "a_id" INTEGER NOT NULL REFERENCES actors(id),
            "s_id" INTEGER NOT NULL REFERENCES tvshows(id),
            PRIMARY KEY(a_id, s_id)
        )''', None, True)

        execute_sql(conn, '''CREATE TABLE "crew_tvshows" (
            "a_id" INTEGER NOT NULL REFERENCES actors(id),
            "s_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "job" TEXT,
            PRIMARY KEY(a_id, s_id)
        )''', None, True)

        execute_sql(conn, '''CREATE TABLE "tvshows_genres" (
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "genre_id" INTEGER NOT NULL REFERENCES genres(id),
            PRIMARY KEY(tvshow_id, genre_id)
        )''', None, True)

        execute_sql(conn, "ALTER TABLE files ADD COLUMN episode_id INTEGER REFERENCES episodes(id)", None, True)
        execute_sql(conn, 'CREATE INDEX "idx_files_episode" ON files(episode_id)', None, True)
        execute_sql(conn, "ALTER TABLE files ADD COLUMN libtype TEXT DEFAULT NULL", None, True)
        execute_sql(conn, "UPDATE files SET libtype = 'movies' WHERE libtype IS NULL", None, True)

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " merge NULL-tmdb_id title duplicates; add partial unique index on tvshows(tmdb_id) "
    if DBVERSION == 11:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        cursor = conn.cursor()
        cursor.execute(
            "SELECT title FROM tvshows WHERE tmdb_id IS NULL GROUP BY title HAVING COUNT(*) > 1"
        )
        dup_titles = [row[0] for row in cursor.fetchall()]
        for title in dup_titles:
            cursor.execute(
                "SELECT id FROM tvshows WHERE title = ? AND tmdb_id IS NULL ORDER BY id ASC", (title,)
            )
            ids = [row[0] for row in cursor.fetchall()]
            master = ids[0]
            for dup in ids[1:]:
                try:
                    cursor.execute("UPDATE episodes SET tvshow_id = ? WHERE tvshow_id = ?", (master, dup))
                except Exception:
                    cursor.execute("DELETE FROM episodes WHERE tvshow_id = ?", (dup,))
                try:
                    cursor.execute("UPDATE seasons SET tvshow_id = ? WHERE tvshow_id = ?", (master, dup))
                except Exception:
                    cursor.execute("DELETE FROM seasons WHERE tvshow_id = ?", (dup,))
                try:
                    cursor.execute("UPDATE actors_tvshows SET s_id = ? WHERE s_id = ?", (master, dup))
                except Exception:
                    cursor.execute("DELETE FROM actors_tvshows WHERE s_id = ?", (dup,))
                try:
                    cursor.execute("UPDATE crew_tvshows SET s_id = ? WHERE s_id = ?", (master, dup))
                except Exception:
                    cursor.execute("DELETE FROM crew_tvshows WHERE s_id = ?", (dup,))
                try:
                    cursor.execute("UPDATE tvshows_genres SET tvshow_id = ? WHERE tvshow_id = ?", (master, dup))
                except Exception:
                    cursor.execute("DELETE FROM tvshows_genres WHERE tvshow_id = ?", (dup,))
                cursor.execute("DELETE FROM tvshows WHERE id = ?", (dup,))
        conn.commit()
        cursor.close()

        execute_sql(conn,
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tvshows_tmdb_id ON tvshows(tmdb_id) WHERE tmdb_id IS NOT NULL",
            None, True)

        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    " files.scan_error_count, files.tvshow_id "
    if DBVERSION == 12:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)

        execute_sql(conn, "ALTER TABLE files ADD COLUMN scan_error_count INTEGER DEFAULT 0", None, True)
        execute_sql(conn, "ALTER TABLE files ADD COLUMN tvshow_id INTEGER REFERENCES tvshows(id)", None, True)
        execute_sql(conn, 'CREATE INDEX "idx_files_tvshow" ON files(tvshow_id)', None, True)
        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    if DBVERSION == 13:
        DBVERSION += 1
        verbose("Upgrading database to version " + str(DBVERSION), 2)
        # Backfill tvshow_id for files that had episode_id set before v13 added the column
        execute_sql(conn,
            "UPDATE files SET tvshow_id = (SELECT e.tvshow_id FROM episodes e WHERE e.id = files.episode_id) "
            "WHERE episode_id IS NOT NULL AND tvshow_id IS NULL",
            None, True)
        execute_sql(conn, f"UPDATE settings SET value_int = {DBVERSION} WHERE dbkey = 'dbversion'", None, True)

    if DBVERSION == 14:
        verbose("Database up-to-date", 1)
