"""guid column (formerly oid) - schema creation, v14 -> v15 rebuild, and repair.

`oid` is an SQLite alias for rowid. SQLite 3.54 rejects ADD/RENAME/DROP COLUMN oid, which
left databases created with it without the column (and with a unique index on rowid).
"""
import glob
import io
import os
import re
import sqlite3
import tokenize

import pytest

from tvthekidx import migration
from tvthekidx.utility import generate_oid

TABLES = ("movies", "files", "actors", "tags", "genres", "tvshows", "seasons", "episodes")
LEFTOVERS = ("poster", "profile", "screenshot", "collection")


def _cols(db, table):
    return [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]


def _indexes(db, table):
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL", (table,))}


def _version(db):
    return db.execute("SELECT value_int FROM settings WHERE dbkey = 'dbversion'").fetchone()[0]


def _make_v14(path, broken=False):
    """Create the 8 guid tables as they look at v14.

    broken=False: real oid column (database created with SQLite <= 3.53).
    broken=True:  movies/files/actors/tags without oid but with the columns the failed
                  migrations left behind, and oid_* indexes that silently index rowid
                  (database created with SQLite >= 3.54).
    """
    db = sqlite3.connect(path)
    for table, ddl in migration._GUID_TABLES.items():
        sql = ddl.format(name=table)
        if broken and table in ("movies", "files", "actors", "tags"):
            sql = re.sub(r'"guid" TEXT DEFAULT NULL,\s*', "", sql)
            extra = {"movies": '"poster" BLOB, ', "actors": '"profile" BLOB, ',
                     "files": '"screenshot" BLOB, "collection" TEXT DEFAULT NULL, ', "tags": ""}[table]
            sql = sql.replace('PRIMARY KEY("id" AUTOINCREMENT)', extra + 'PRIMARY KEY("id" AUTOINCREMENT)', 1)
        else:
            sql = sql.replace('"guid"', '"oid"')
        db.execute(sql)
    for table in ("movies", "files", "actors", "tags", "tvshows", "seasons", "episodes"):
        db.execute(f'CREATE UNIQUE INDEX "oid_{table}" ON "{table}" ("oid")')
    db.execute('CREATE UNIQUE INDEX "unique_fn" ON "files" ("collection_id", "filename", "relpath")')
    db.execute('CREATE INDEX "idx_files_tvshow" ON files(tvshow_id)')
    db.execute("CREATE UNIQUE INDEX idx_tvshows_tmdb_id ON tvshows(tmdb_id) WHERE tmdb_id IS NOT NULL")
    db.execute('CREATE TABLE "collections" ("id" INTEGER PRIMARY KEY, "guid" TEXT, "name" TEXT)')
    db.execute('CREATE TABLE "actors_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, PRIMARY KEY("a_id","m_id"))')
    db.execute('CREATE TABLE "crew_movies" ("a_id" INTEGER NOT NULL, "m_id" INTEGER NOT NULL, "job" TEXT, PRIMARY KEY("a_id","m_id"))')
    db.execute('CREATE TABLE "movies_genres" ("movie_id" INTEGER NOT NULL, "genre_id" INTEGER NOT NULL, PRIMARY KEY("movie_id","genre_id"))')
    db.execute('CREATE TABLE "attachments" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "type" TEXT NOT NULL, "data" BLOB, "ref_id" INTEGER)')
    db.execute("INSERT INTO collections VALUES (1, 'c-guid', 'Movies')")
    db.execute('CREATE TABLE "settings" ("dbkey" TEXT, "value_int" INTEGER, "value_str" TEXT, PRIMARY KEY("dbkey"))')
    db.execute("INSERT INTO settings VALUES ('dbversion', 14, NULL)")

    oid = [] if broken else ["oid"]

    def ins(table, row):
        row = {k: v for k, v in row.items() if k != "oid" or oid}
        db.execute(f'INSERT INTO "{table}" ({", ".join(row)}) VALUES ({", ".join("?" * len(row))})', list(row.values()))
    ins("movies", {"id": 7, "title": "Film", "title_orig": "Film", "year": 2001, "tmdb_id": 11, "oid": "m-oid"})
    ins("files", {"id": 3, "filename": "Film (2001).mkv", "relpath": ".", "collection_id": 1, "movie_id": 7, "oid": "f-oid"})
    ins("actors", {"id": 5, "name": "Actor", "tmdb_id": 22, "oid": "a-oid"})
    ins("tags", {"id": 2, "tag": "HD", "oid": "t-oid"})
    db.execute("INSERT INTO genres (id, tmdb_id, name, oid) VALUES (4, 33, 'Drama', 'g-oid')")
    db.execute("INSERT INTO tvshows (id, title, title_orig, year, tmdb_id, oid) VALUES (8, 'Show', 'Show', 2010, 44, 's-oid')")
    db.execute("INSERT INTO seasons (id, tvshow_id, season_number, oid) VALUES (9, 8, 1, 'se-oid')")
    db.execute("INSERT INTO episodes (id, tvshow_id, season_id, season_number, episode_number, oid) VALUES (10, 8, 9, 1, 1, 'e-oid')")
    db.commit()
    db.close()


def test_new_database_has_guid_everywhere(tmp_path):
    db = migration.initialize_db(str(tmp_path / "new.db"))
    assert _version(db) == 15
    for table in TABLES:
        cols = _cols(db, table)
        assert "guid" in cols and "oid" not in cols, table
        assert not set(cols) & set(LEFTOVERS), table
        assert f"guid_{table}" in _indexes(db, table)
    db.close()


def test_v14_with_oid_column_is_renamed(tmp_path):
    path = str(tmp_path / "v14.db")
    _make_v14(path)
    db = migration.initialize_db(path)
    assert _version(db) == 15
    expected = {"movies": "m-oid", "files": "f-oid", "actors": "a-oid", "tags": "t-oid", "genres": "g-oid",
                "tvshows": "s-oid", "seasons": "se-oid", "episodes": "e-oid"}
    for table, guid in expected.items():
        assert "oid" not in _cols(db, table)
        assert [tuple(r) for r in db.execute(f'SELECT guid FROM "{table}"')] == [(guid,)], table
        assert f"guid_{table}" in _indexes(db, table)
        assert not any(name.startswith("oid_") for name in _indexes(db, table))
    # other indexes and data survive the rebuild
    assert {"unique_fn", "idx_files_tvshow"} <= _indexes(db, "files")
    assert "idx_tvshows_tmdb_id" in _indexes(db, "tvshows")
    assert tuple(db.execute("SELECT id, movie_id, collection_id FROM files").fetchone()) == (3, 7, 1)
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    # AUTOINCREMENT keeps counting after the rebuild
    db.execute("INSERT INTO movies (title, title_orig, year) VALUES ('Next', 'Next', 2002)")
    assert db.execute("SELECT MAX(id) FROM movies").fetchone()[0] == 8
    db.close()


def test_v14_broken_by_sqlite_354_is_repaired(tmp_path):
    path = str(tmp_path / "broken.db")
    _make_v14(path, broken=True)
    db = migration.initialize_db(path)
    assert _version(db) == 15
    for table in TABLES:
        cols = _cols(db, table)
        assert "guid" in cols and "oid" not in cols, table
        assert not set(cols) & set(LEFTOVERS), table
    # guid backfilled with the same keys the insert functions use
    assert db.execute("SELECT guid FROM movies").fetchone()[0] == generate_oid("movie", "11")
    assert db.execute("SELECT guid FROM files").fetchone()[0] == generate_oid("file", "1:.:Film (2001).mkv")
    assert db.execute("SELECT guid FROM actors").fetchone()[0] == generate_oid("actor", "22")
    assert db.execute("SELECT guid FROM tags").fetchone()[0] == generate_oid("tag", "HD")
    # the oid_* indexes on rowid are gone
    assert not any(n.startswith("oid_") for t in TABLES for n in _indexes(db, t))
    db.close()


def test_upgrade_is_idempotent(tmp_path):
    path = str(tmp_path / "v14.db")
    _make_v14(path)
    migration.initialize_db(path).close()
    db = migration.initialize_db(path)
    assert _version(db) == 15
    assert db.execute("SELECT guid FROM movies").fetchone()[0] == "m-oid"
    db.close()


_SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|WHERE|JOIN|INDEX|CREATE|ALTER)\b", re.I)
_OID = re.compile(r"\boid\b")


@pytest.mark.parametrize("path", sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "src", "tvthekidx", "*.py"))))
def test_no_sql_references_oid(path):
    """A forgotten `x.oid` in SQL would not fail: it silently returns the integer rowid."""
    if path.endswith("migration.py"):
        return  # the v15 rebuild reads the old oid column on purpose
    with open(path, encoding="utf-8") as f:
        src = f.read()
    kinds = {tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", tokenize.STRING)}
    bad = [(t.start[0], t.string) for t in tokenize.generate_tokens(io.StringIO(src).readline)
           if t.type in kinds and _OID.search(t.string) and (_SQL.search(t.string) or t.string.strip("'\"") == "oid")]
    assert bad == []


def _movie(db, title, tmdb_id, guid_col=None, guid=None):
    cols, vals = ["title", "title_orig", "year", "tmdb_id"], [title, title, 2001, tmdb_id]
    if guid_col:
        cols.append(guid_col)
        vals.append(guid)
    return db.execute(f"INSERT INTO movies ({', '.join(cols)}) VALUES ({', '.join('?' * len(vals))})", vals).lastrowid


def test_duplicate_movies_are_merged_in_v6(tmp_path):
    """Two rows for one TMDB id used to make the unique index fail silently (no index at all)."""
    path = str(tmp_path / "v5.db")
    db = migration.initialize_db(path, target=5)
    keep = _movie(db, "Der Wüstenplanet", 841)
    dup = _movie(db, "Dune", 841)
    db.execute("INSERT INTO actors (id, name, tmdb_id) VALUES (1, 'A', 1), (2, 'B', 2)")
    db.execute("INSERT INTO actors_movies (a_id, m_id) VALUES (1, ?), (1, ?), (2, ?)", (keep, dup, dup))
    db.execute("INSERT INTO crew_movies (a_id, m_id, job) VALUES (2, ?, 'Director')", (dup,))
    db.execute("INSERT INTO files (collection, filename, relpath, movie_id) VALUES ('c', 'b.mkv', '.', ?)", (dup,))
    db.commit()
    db.close()

    db = migration.initialize_db(path)
    assert _version(db) == migration.LATEST_VERSION
    assert [r[0] for r in db.execute("SELECT id FROM movies")] == [keep]
    assert db.execute("SELECT movie_id FROM files").fetchone()[0] == keep
    assert sorted(r[0] for r in db.execute("SELECT a_id FROM actors_movies WHERE m_id = ?", (keep,))) == [1, 2]
    assert tuple(db.execute("SELECT a_id, job FROM crew_movies WHERE m_id = ?", (keep,)).fetchone()) == (2, "Director")
    assert "guid_movies" in _indexes(db, "movies")
    db.close()


def test_duplicate_movies_are_merged_in_v15(tmp_path):
    """v14 databases whose oid_movies index was never created (duplicates) get merged and indexed."""
    path = str(tmp_path / "v14.db")
    _make_v14(path)
    db = sqlite3.connect(path)
    db.execute('DROP INDEX "oid_movies"')
    dup = _movie(db, "Film again", 11, "oid", "m-oid")  # same TMDB id and oid as movie 7
    db.execute("INSERT INTO movies_genres (movie_id, genre_id) VALUES (?, 4)", (dup,))
    db.execute("INSERT INTO attachments (type, data, ref_id) VALUES ('poster', x'00', ?)", (dup,))
    db.commit()
    db.close()

    db = migration.initialize_db(path)
    assert [tuple(r) for r in db.execute("SELECT id, guid FROM movies")] == [(7, "m-oid")]
    assert [tuple(r) for r in db.execute("SELECT movie_id, genre_id FROM movies_genres")] == [(7, 4)]
    assert [tuple(r) for r in db.execute("SELECT type, ref_id FROM attachments")] == [("poster", 7)]
    assert "guid_movies" in _indexes(db, "movies")
    db.close()


def test_failed_step_raises_and_rolls_back(tmp_path):
    path = str(tmp_path / "v12.db")
    migration.initialize_db(path, target=12).close()
    db = sqlite3.connect(path)
    db.execute("ALTER TABLE files ADD COLUMN scan_error_count INTEGER")  # makes the v13 step fail
    db.commit()
    db.close()

    with pytest.raises(migration.MigrationError, match="version 13"):
        migration.upgrade_db(path)
    db = sqlite3.connect(path)
    assert _version(db) == 12
    assert "tvshow_id" not in _cols(db, "files")  # the step's earlier statements were rolled back
    db.close()
