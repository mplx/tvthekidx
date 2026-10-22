# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import os
import sqlite3

from .database import create_connection
from .utility import verbose, normalize_string, generate_oid


class MigrationError(Exception):
    """A schema upgrade step failed; the database stays at the previous version."""


def initialize_db(db_file, target=None):
    createMode = not os.path.isfile(db_file)

    if createMode:
        verbose("Creating database...", 2)
        conn = create_connection(db_file)

        verbose("Creating table movies...", 3)
        conn.execute('CREATE TABLE "movies" ("id" INTEGER NOT NULL, "title" TEXT NOT NULL, "title_orig" TEXT NOT NULL, "year" INTEGER NOT NULL, "description" TEXT, "popularity" REAL DEFAULT 0, "score" REAL DEFAULT 0, "poster" BLOB, "tmdb_id" INTEGER, PRIMARY KEY("id" AUTOINCREMENT) )')

        verbose("Creating table files...", 3)
        conn.execute('CREATE TABLE "files" ("id" INTEGER, "collection" TEXT DEFAULT NULL, "filename" TEXT NOT NULL, "relpath" TEXT DEFAULT NULL, "size" INTEGER DEFAULT NULL, "ctime" INTEGER DEFAULT NULL, "mtime" INTEGER DEFAULT NULL, "movie_id" INTEGER, "added" INTEGER default (cast(strftime(\'%s\',\'now\') as int)), "lastmod" INTEGER default (cast(strftime(\'%s\',\'now\') as int)), PRIMARY KEY("id" AUTOINCREMENT), FOREIGN KEY("movie_id") REFERENCES"movies"("id"))')

        verbose("Creating table actors...", 3)
        conn.execute('CREATE TABLE "actors" ("id" INTEGER, "name" TEXT NOT NULL, "popularity" REAL, "profile" BLOB, "tmdb_id" INTEGER NOT NULL UNIQUE, PRIMARY KEY("id" AUTOINCREMENT))')

        verbose("Creating table actors/movies...", 3)
        conn.execute('CREATE TABLE "actors_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, FOREIGN KEY("m_id") REFERENCES "movies"("id"), FOREIGN KEY("a_id") REFERENCES "actors"("id"), PRIMARY KEY("a_id","m_id"))')

        verbose("Creating table indices...", 3)
        conn.execute('CREATE UNIQUE INDEX "unique_fn" ON "files" ("collection" ASC, "filename" ASC, "relpath" ASC)')
        conn.commit()

    else:
        verbose("Connecting database...", 2)
        conn = create_connection(db_file)

    upgrade_db(db_file, target)

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def upgrade_db(db_file, target=None):
    """Apply all pending schema steps (or up to version `target`).

    Each step runs in one transaction together with the version bump: it is applied
    completely or not at all. A failing step raises MigrationError instead of being
    logged and skipped, so a database never claims a version whose schema it lacks.
    """
    verbose("Opening database...", 3)
    conn = create_connection(db_file)
    conn.isolation_level = None  # explicit BEGIN/COMMIT per step
    try:
        verbose("Getting database version...", 3)
        if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'").fetchone() is None:
            verbose("Creating settings table...", 3)
            conn.execute("BEGIN")
            conn.execute('CREATE TABLE "settings" ("dbkey" TEXT, "value_int" INTEGER, "value_str" TEXT, PRIMARY KEY("dbkey"))')
            conn.execute("INSERT INTO \"settings\" (\"dbkey\", \"value_int\", \"value_str\") VALUES ('dbversion', 1, NULL)")
            conn.execute("COMMIT")
        version = conn.execute("SELECT value_int FROM settings WHERE dbkey='dbversion'").fetchone()[0]
        verbose("Database version " + str(version) + " found", 2)

        for step_version, description, step in _STEPS:
            if version != step_version - 1 or (target is not None and step_version > target):
                continue
            verbose("Upgrading database to version " + str(step_version), 2)
            conn.execute("BEGIN")
            try:
                step(conn)
                conn.execute("UPDATE settings SET value_int = ? WHERE dbkey = 'dbversion'", (step_version,))
                conn.execute("COMMIT")
            except Exception as e:
                conn.execute("ROLLBACK")
                raise MigrationError(
                    f"Upgrading database '{db_file}' to version {step_version} ({description}) failed: {e}. "
                    f"The database is unchanged at version {version}.") from e
            version = step_version

        if version == LATEST_VERSION:
            verbose("Database up-to-date", 1)
    finally:
        conn.close()


def _v2(conn):
    conn.execute('ALTER TABLE files ADD COLUMN width INTEGER')
    conn.execute('ALTER TABLE files ADD COLUMN height INTEGER')
    conn.execute('ALTER TABLE files ADD COLUMN duration REAL')
    conn.execute('ALTER TABLE files ADD COLUMN codec TEXT')
    conn.execute('ALTER TABLE files ADD COLUMN screenshot BLOB')


def _v3(conn):
    conn.execute('CREATE TABLE "crew_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, "job" TEXT, FOREIGN KEY("m_id") REFERENCES "movies"("id"), FOREIGN KEY("a_id") REFERENCES "actors"("id"), PRIMARY KEY("a_id","m_id"))')


def _v4(conn):
    conn.execute('CREATE TABLE "tags" ("id" INTEGER, "tag" TEXT NOT NULL UNIQUE, PRIMARY KEY("id" AUTOINCREMENT))')
    conn.execute('CREATE TABLE "files_tags" ("f_id" INTEGER, "t_id" INTEGER, PRIMARY KEY("f_id","t_id"), FOREIGN KEY("t_id") REFERENCES "tags"("id"), FOREIGN KEY("f_id") REFERENCES "files"("id"))')
    conn.execute('CREATE TABLE "tags_regex" ("id" INTEGER, "t_id" INTEGER, "regex" TEXT, FOREIGN KEY("t_id") REFERENCES "tags"("id"), PRIMARY KEY("id"))')


def _v5(conn):
    conn.execute("ALTER TABLE movies ADD COLUMN title_normalized TEXT")
    rows = conn.execute("SELECT id, title FROM movies").fetchall()
    conn.executemany("UPDATE movies SET title_normalized = ? WHERE id = ?",
                     [(normalize_string(title if title else ""), row_id) for row_id, title in rows])


def _v6(conn):
    conn.execute("ALTER TABLE files ADD COLUMN tvstation TEXT DEFAULT NULL")
    conn.execute("ALTER TABLE files ADD COLUMN lastseen INTEGER DEFAULT NULL")
    conn.execute("UPDATE files SET lastseen = cast(strftime('%s','now') as int)")
    # The column was named oid before v15; see _v15 and _rebuild_with_guid.
    conn.execute("ALTER TABLE movies ADD COLUMN guid TEXT DEFAULT NULL")
    conn.execute("ALTER TABLE files  ADD COLUMN guid TEXT DEFAULT NULL")
    conn.execute("ALTER TABLE actors ADD COLUMN guid TEXT DEFAULT NULL")
    conn.execute("ALTER TABLE tags   ADD COLUMN guid TEXT DEFAULT NULL")

    rows = conn.execute("SELECT id, tmdb_id, title, year FROM movies").fetchall()
    conn.executemany("UPDATE movies SET guid = ? WHERE id = ?",
                     [(generate_oid("movie", str(r[1]) if r[1] else f"{r[2]}:{r[3]}"), r[0]) for r in rows])
    rows = conn.execute("SELECT id, collection, relpath, filename FROM files").fetchall()
    conn.executemany("UPDATE files SET guid = ? WHERE id = ?",
                     [(generate_oid("file", f"{r[1]}:{r[2]}:{r[3]}"), r[0]) for r in rows])
    rows = conn.execute("SELECT id, tmdb_id FROM actors").fetchall()
    conn.executemany("UPDATE actors SET guid = ? WHERE id = ?", [(generate_oid("actor", str(r[1])), r[0]) for r in rows])
    rows = conn.execute("SELECT id, tag FROM tags").fetchall()
    conn.executemany("UPDATE tags SET guid = ? WHERE id = ?", [(generate_oid("tag", r[1]), r[0]) for r in rows])

    _merge_duplicate_movies(conn)
    conn.execute('CREATE UNIQUE INDEX "guid_movies" ON "movies" ("guid")')
    conn.execute('CREATE UNIQUE INDEX "guid_files"  ON "files"  ("guid")')
    conn.execute('CREATE UNIQUE INDEX "guid_actors" ON "actors" ("guid")')
    conn.execute('CREATE UNIQUE INDEX "guid_tags"   ON "tags"   ("guid")')


def _v7(conn):
    conn.execute('CREATE TABLE "files_attachments" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "type" TEXT NOT NULL, "data" BLOB)')
    conn.execute('CREATE TABLE "files_attachments_map" ("f_id" INTEGER NOT NULL, "a_id" INTEGER NOT NULL, PRIMARY KEY("f_id","a_id"), FOREIGN KEY("f_id") REFERENCES "files"("id"), FOREIGN KEY("a_id") REFERENCES "files_attachments"("id"))')
    for f_id, screenshot in conn.execute("SELECT id, screenshot FROM files WHERE screenshot IS NOT NULL").fetchall():
        att_id = conn.execute("INSERT INTO files_attachments (type, data) VALUES ('screenshot', ?)", (screenshot,)).lastrowid
        conn.execute("INSERT INTO files_attachments_map (f_id, a_id) VALUES (?, ?)", (f_id, att_id))
    conn.execute("ALTER TABLE files DROP COLUMN screenshot")

    conn.execute("ALTER TABLE files_attachments ADD COLUMN ref_id INTEGER DEFAULT NULL")
    for row in conn.execute("SELECT id, poster FROM movies WHERE poster IS NOT NULL").fetchall():
        conn.execute("INSERT INTO files_attachments (type, data, ref_id) VALUES ('poster', ?, ?)", (row[1], row[0]))
    for row in conn.execute("SELECT id, profile FROM actors WHERE profile IS NOT NULL").fetchall():
        conn.execute("INSERT INTO files_attachments (type, data, ref_id) VALUES ('profile', ?, ?)", (row[1], row[0]))
    conn.execute("ALTER TABLE movies DROP COLUMN poster")
    conn.execute("ALTER TABLE actors DROP COLUMN profile")


def _v8(conn):
    conn.execute("UPDATE files_attachments SET ref_id = (SELECT f_id FROM files_attachments_map WHERE a_id = files_attachments.id) WHERE type = 'screenshot'")
    conn.execute('DROP TABLE "files_attachments_map"')
    conn.execute('ALTER TABLE "files_attachments" RENAME TO "attachments"')
    conn.execute('CREATE INDEX "idx_attachments_ref_type" ON "attachments" ("ref_id", "type")')


def _v9(conn):
    conn.execute('CREATE TABLE "genres" ("id" INTEGER NOT NULL, "tmdb_id" INTEGER NOT NULL UNIQUE, "name" TEXT NOT NULL, "guid" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))')
    conn.execute('CREATE TABLE "movies_genres" ("movie_id" INTEGER NOT NULL, "genre_id" INTEGER NOT NULL, PRIMARY KEY("movie_id","genre_id"), FOREIGN KEY("movie_id") REFERENCES "movies"("id"), FOREIGN KEY("genre_id") REFERENCES "genres"("id"))')
    conn.execute("ALTER TABLE movies ADD COLUMN cast_error_count INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE movies ADD COLUMN genre_error_count INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE movies ADD COLUMN refresh_timestamp INTEGER DEFAULT NULL")


def _v10(conn):
    conn.execute('CREATE TABLE "collections" ("id" INTEGER NOT NULL, "guid" TEXT NOT NULL UNIQUE, "name" TEXT NOT NULL UNIQUE, "movie_filename_regex" TEXT DEFAULT NULL, "tvshow_filename_regex" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))')
    for (name,) in conn.execute("SELECT DISTINCT collection FROM files WHERE collection IS NOT NULL").fetchall():
        conn.execute("INSERT INTO collections (guid, name) VALUES (?, ?)", (generate_oid("collection", name), name))

    conn.execute("ALTER TABLE files ADD COLUMN collection_id INTEGER REFERENCES collections(id)")
    conn.execute("UPDATE files SET collection_id = (SELECT id FROM collections WHERE name = files.collection)")
    conn.execute('DROP INDEX IF EXISTS "unique_fn"')
    conn.execute('CREATE UNIQUE INDEX "unique_fn" ON "files" ("collection_id", "filename", "relpath")')
    conn.execute("ALTER TABLE files DROP COLUMN collection")


def _v11(conn):
    conn.execute('''CREATE TABLE "tvshows" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "title" TEXT NOT NULL,
            "title_orig" TEXT NOT NULL,
            "title_normalized" TEXT,
            "year" INTEGER NOT NULL,
            "description" TEXT,
            "popularity" REAL DEFAULT 0,
            "score" REAL DEFAULT 0,
            "tmdb_id" INTEGER,
            "guid" TEXT,
            "cast_error_count" INTEGER DEFAULT 0,
            "genre_error_count" INTEGER DEFAULT 0,
            "season_error_count" INTEGER DEFAULT 0,
            "refresh_timestamp" INTEGER DEFAULT NULL
        )''')
    conn.execute('CREATE UNIQUE INDEX "guid_tvshows" ON tvshows (guid)')

    conn.execute('''CREATE TABLE "seasons" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "season_number" INTEGER NOT NULL,
            "title" TEXT,
            "year" INTEGER,
            "guid" TEXT,
            UNIQUE(tvshow_id, season_number)
        )''')
    conn.execute('CREATE UNIQUE INDEX "guid_seasons" ON seasons (guid)')

    conn.execute('''CREATE TABLE "episodes" (
            "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "season_id" INTEGER NOT NULL REFERENCES seasons(id),
            "season_number" INTEGER NOT NULL,
            "episode_number" INTEGER NOT NULL,
            "title" TEXT,
            "year" INTEGER,
            "description" TEXT,
            "score" REAL DEFAULT 0,
            "guid" TEXT,
            UNIQUE(tvshow_id, season_number, episode_number)
        )''')
    conn.execute('CREATE UNIQUE INDEX "guid_episodes" ON episodes (guid)')

    conn.execute('''CREATE TABLE "actors_tvshows" (
            "a_id" INTEGER NOT NULL REFERENCES actors(id),
            "s_id" INTEGER NOT NULL REFERENCES tvshows(id),
            PRIMARY KEY(a_id, s_id)
        )''')

    conn.execute('''CREATE TABLE "crew_tvshows" (
            "a_id" INTEGER NOT NULL REFERENCES actors(id),
            "s_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "job" TEXT,
            PRIMARY KEY(a_id, s_id)
        )''')

    conn.execute('''CREATE TABLE "tvshows_genres" (
            "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id),
            "genre_id" INTEGER NOT NULL REFERENCES genres(id),
            PRIMARY KEY(tvshow_id, genre_id)
        )''')

    conn.execute("ALTER TABLE files ADD COLUMN episode_id INTEGER REFERENCES episodes(id)")
    conn.execute('CREATE INDEX "idx_files_episode" ON files(episode_id)')
    conn.execute("ALTER TABLE files ADD COLUMN libtype TEXT DEFAULT NULL")
    conn.execute("UPDATE files SET libtype = 'movies' WHERE libtype IS NULL")


def _v12(conn):
    dup_titles = [row[0] for row in conn.execute(
        "SELECT title FROM tvshows WHERE tmdb_id IS NULL GROUP BY title HAVING COUNT(*) > 1").fetchall()]
    for title in dup_titles:
        ids = [row[0] for row in conn.execute(
            "SELECT id FROM tvshows WHERE title = ? AND tmdb_id IS NULL ORDER BY id ASC", (title,)).fetchall()]
        master = ids[0]
        for dup in ids[1:]:
            for update, delete in (
                    ("UPDATE episodes SET tvshow_id = ? WHERE tvshow_id = ?", "DELETE FROM episodes WHERE tvshow_id = ?"),
                    ("UPDATE seasons SET tvshow_id = ? WHERE tvshow_id = ?", "DELETE FROM seasons WHERE tvshow_id = ?"),
                    ("UPDATE actors_tvshows SET s_id = ? WHERE s_id = ?", "DELETE FROM actors_tvshows WHERE s_id = ?"),
                    ("UPDATE crew_tvshows SET s_id = ? WHERE s_id = ?", "DELETE FROM crew_tvshows WHERE s_id = ?"),
                    ("UPDATE tvshows_genres SET tvshow_id = ? WHERE tvshow_id = ?", "DELETE FROM tvshows_genres WHERE tvshow_id = ?")):
                try:
                    conn.execute(update, (master, dup))
                except sqlite3.IntegrityError:  # rows the master already has
                    conn.execute(delete, (dup,))
            conn.execute("DELETE FROM tvshows WHERE id = ?", (dup,))

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tvshows_tmdb_id ON tvshows(tmdb_id) WHERE tmdb_id IS NOT NULL")


def _v13(conn):
    conn.execute("ALTER TABLE files ADD COLUMN scan_error_count INTEGER DEFAULT 0")
    conn.execute("ALTER TABLE files ADD COLUMN tvshow_id INTEGER REFERENCES tvshows(id)")
    conn.execute('CREATE INDEX "idx_files_tvshow" ON files(tvshow_id)')


def _v14(conn):
    # Backfill tvshow_id for files that had episode_id set before v13 added the column
    conn.execute("UPDATE files SET tvshow_id = (SELECT e.tvshow_id FROM episodes e WHERE e.id = files.episode_id) "
                 "WHERE episode_id IS NOT NULL AND tvshow_id IS NULL")


def _v15(conn):
    for table, ddl in _GUID_TABLES.items():
        _rebuild_with_guid(conn, table, ddl)
        if table == "movies":
            _merge_duplicate_movies(conn)
        conn.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "guid_{table}" ON "{table}" ("guid")')


# (version, description, step): step N upgrades a database at version N - 1.
_STEPS = (
    (2, "ffmpeg probe columns", _v2),
    (3, "crew", _v3),
    (4, "tags", _v4),
    (5, "title normalization", _v5),
    (6, "tvstation, lastseen, guid", _v6),
    (7, "files_attachments table, poster/profile migration", _v7),
    (8, "attachments table, screenshots to ref_id", _v8),
    (9, "genres, error counters", _v9),
    (10, "collections table, collection_id", _v10),
    (11, "tvshows, seasons, episodes, TV junction tables, files.episode_id, files.libtype", _v11),
    (12, "merge NULL-tmdb_id tvshow duplicates, unique tvshows(tmdb_id)", _v12),
    (13, "files.scan_error_count, files.tvshow_id", _v13),
    (14, "backfill files.tvshow_id", _v14),
    (15, "rename oid -> guid (oid is a rowid alias), repair databases created with SQLite >= 3.54", _v15),
)
LATEST_VERSION = _STEPS[-1][0]


def _merge_duplicate_movies(conn):
    """Merge movie rows that share a guid (the same TMDB id, or title and year).

    Such rows come from indexing the same movie under two file names; they would make
    the unique guid index fail and map two movies to one exported page. The lowest id
    is kept; files, cast, crew and genres move to it, and the duplicate's poster is
    used only if the kept row has none. Works on the schema as of v6 and later.
    """
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    groups = conn.execute(
        "SELECT guid, GROUP_CONCAT(id) FROM movies WHERE guid IS NOT NULL GROUP BY guid HAVING COUNT(*) > 1").fetchall()
    for guid, ids in groups:
        ids = sorted(int(i) for i in ids.split(","))
        master, dups = ids[0], ids[1:]
        verbose(f"Merging duplicate movie {dups} into {master} ({guid})", 1)
        for dup in dups:
            conn.execute("UPDATE files SET movie_id = ? WHERE movie_id = ?", (master, dup))
            conn.execute("INSERT OR IGNORE INTO actors_movies (a_id, m_id) SELECT a_id, ? FROM actors_movies WHERE m_id = ?", (master, dup))
            conn.execute("DELETE FROM actors_movies WHERE m_id = ?", (dup,))
            if "crew_movies" in tables:
                conn.execute("INSERT OR IGNORE INTO crew_movies (a_id, m_id, job) SELECT a_id, ?, job FROM crew_movies WHERE m_id = ?", (master, dup))
                conn.execute("DELETE FROM crew_movies WHERE m_id = ?", (dup,))
            if "movies_genres" in tables:
                conn.execute("INSERT OR IGNORE INTO movies_genres (movie_id, genre_id) SELECT ?, genre_id FROM movies_genres WHERE movie_id = ?", (master, dup))
                conn.execute("DELETE FROM movies_genres WHERE movie_id = ?", (dup,))
            if "attachments" in tables:
                conn.execute("UPDATE attachments SET ref_id = ? WHERE type = 'poster' AND ref_id = ? "
                             "AND NOT EXISTS (SELECT 1 FROM attachments WHERE type = 'poster' AND ref_id = ?)", (master, dup, master))
                conn.execute("DELETE FROM attachments WHERE type = 'poster' AND ref_id = ?", (dup,))
            conn.execute("DELETE FROM movies WHERE id = ?", (dup,))


# Target schema of every table carrying a guid column (v15). Used by the v14 -> v15
# rebuild; older migration steps keep their own DDL.
_GUID_TABLES = {
    "movies": '''CREATE TABLE "{name}" ("id" INTEGER NOT NULL, "title" TEXT NOT NULL, "title_orig" TEXT NOT NULL,
        "year" INTEGER NOT NULL, "description" TEXT, "popularity" REAL DEFAULT 0, "score" REAL DEFAULT 0,
        "tmdb_id" INTEGER, "title_normalized" TEXT, "guid" TEXT DEFAULT NULL, "cast_error_count" INTEGER DEFAULT 0,
        "genre_error_count" INTEGER DEFAULT 0, "refresh_timestamp" INTEGER DEFAULT NULL,
        PRIMARY KEY("id" AUTOINCREMENT))''',
    "files": '''CREATE TABLE "{name}" ("id" INTEGER, "filename" TEXT NOT NULL, "relpath" TEXT DEFAULT NULL,
        "size" INTEGER DEFAULT NULL, "ctime" INTEGER DEFAULT NULL, "mtime" INTEGER DEFAULT NULL, "movie_id" INTEGER,
        "added" INTEGER DEFAULT (cast(strftime('%s','now') as int)),
        "lastmod" INTEGER DEFAULT (cast(strftime('%s','now') as int)),
        "width" INTEGER, "height" INTEGER, "duration" REAL, "codec" TEXT, "tvstation" TEXT DEFAULT NULL,
        "lastseen" INTEGER DEFAULT NULL, "guid" TEXT DEFAULT NULL,
        "collection_id" INTEGER REFERENCES collections(id), "episode_id" INTEGER REFERENCES episodes(id),
        "libtype" TEXT DEFAULT NULL, "scan_error_count" INTEGER DEFAULT 0, "tvshow_id" INTEGER REFERENCES tvshows(id),
        PRIMARY KEY("id" AUTOINCREMENT), FOREIGN KEY("movie_id") REFERENCES "movies"("id"))''',
    "actors": '''CREATE TABLE "{name}" ("id" INTEGER, "name" TEXT NOT NULL, "popularity" REAL,
        "tmdb_id" INTEGER NOT NULL UNIQUE, "guid" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))''',
    "tags": '''CREATE TABLE "{name}" ("id" INTEGER, "tag" TEXT NOT NULL UNIQUE, "guid" TEXT DEFAULT NULL,
        PRIMARY KEY("id" AUTOINCREMENT))''',
    "genres": '''CREATE TABLE "{name}" ("id" INTEGER NOT NULL, "tmdb_id" INTEGER NOT NULL UNIQUE, "name" TEXT NOT NULL,
        "guid" TEXT DEFAULT NULL, PRIMARY KEY("id" AUTOINCREMENT))''',
    "tvshows": '''CREATE TABLE "{name}" ("id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "title" TEXT NOT NULL,
        "title_orig" TEXT NOT NULL, "title_normalized" TEXT, "year" INTEGER NOT NULL, "description" TEXT,
        "popularity" REAL DEFAULT 0, "score" REAL DEFAULT 0, "tmdb_id" INTEGER, "guid" TEXT,
        "cast_error_count" INTEGER DEFAULT 0, "genre_error_count" INTEGER DEFAULT 0,
        "season_error_count" INTEGER DEFAULT 0, "refresh_timestamp" INTEGER DEFAULT NULL)''',
    "seasons": '''CREATE TABLE "{name}" ("id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id), "season_number" INTEGER NOT NULL, "title" TEXT,
        "year" INTEGER, "guid" TEXT, UNIQUE(tvshow_id, season_number))''',
    "episodes": '''CREATE TABLE "{name}" ("id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        "tvshow_id" INTEGER NOT NULL REFERENCES tvshows(id), "season_id" INTEGER NOT NULL REFERENCES seasons(id),
        "season_number" INTEGER NOT NULL, "episode_number" INTEGER NOT NULL, "title" TEXT, "year" INTEGER,
        "description" TEXT, "score" REAL DEFAULT 0, "guid" TEXT,
        UNIQUE(tvshow_id, season_number, episode_number))''',
}

# guid for rows that have none: databases created with SQLite >= 3.54 before v15 never got
# an oid column. Same keys as the insert functions in database.py / tags.py.
_GUID_BACKFILL = {
    "movies": ("SELECT id, tmdb_id, title, year FROM movies WHERE guid IS NULL",
               lambda r: generate_oid("movie", str(r[1]) if r[1] else f"{r[2]}:{r[3]}")),
    "files": ("SELECT id, collection_id, relpath, filename FROM files WHERE guid IS NULL",
              lambda r: generate_oid("file", f"{r[1]}:{r[2]}:{r[3]}")),
    "actors": ("SELECT id, tmdb_id FROM actors WHERE guid IS NULL",
               lambda r: generate_oid("actor", str(r[1]))),
    "tags": ("SELECT id, tag FROM tags WHERE guid IS NULL",
             lambda r: generate_oid("tag", r[1])),
    "genres": ("SELECT id, tmdb_id FROM genres WHERE guid IS NULL",
               lambda r: generate_oid("genre", str(r[1]))),
}


def _rebuild_with_guid(conn, table, ddl):
    """Rebuild `table` with a guid column replacing oid. Runs inside the v15 transaction.

    oid is an alias for rowid. Up to SQLite 3.53 ALTER TABLE could add, rename and drop a
    real column named oid; from 3.54 on all three are rejected ("cannot add/rename
    from/drop rowid alias: oid"), so the column can only be changed by rebuilding the table
    (https://sqlite.org/lang_altertable.html#otheralter). Also drops columns left behind by
    migrations that failed on such databases (poster, profile, screenshot, collection).
    Foreign keys are not enforced on the upgrade connection (create_connection leaves
    them off), so dropping a referenced table is fine.
    """
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]
    if not cols or "guid" in cols:
        return
    verbose(f"Rebuilding table {table} with guid column", 2)
    has_oid = "oid" in cols  # PRAGMA table_info lists declared columns only, never the rowid alias

    new = f"{table}_v15"
    indexes = [r[0] for r in conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL "
        "AND name NOT LIKE 'oid\\_%' ESCAPE '\\' AND name NOT LIKE 'guid\\_%' ESCAPE '\\'", (table,))]
    conn.execute(ddl.format(name=new))
    new_cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{new}")')]
    common = [c for c in new_cols if c in cols and c != "guid"]
    target = ", ".join(f'"{c}"' for c in common + ["guid"])
    source = ", ".join([f'"{c}"' for c in common] + ['"oid"' if has_oid else "NULL"])
    conn.execute(f'INSERT INTO "{new}" ({target}) SELECT {source} FROM "{table}"')
    conn.execute(f'DROP TABLE "{table}"')
    conn.execute(f'ALTER TABLE "{new}" RENAME TO "{table}"')
    for sql in indexes:
        conn.execute(sql)
    if table in _GUID_BACKFILL:
        select, make = _GUID_BACKFILL[table]
        updates = [(make(r), r[0]) for r in conn.execute(select).fetchall()]
        conn.executemany(f'UPDATE "{table}" SET guid = ? WHERE id = ?', updates)
