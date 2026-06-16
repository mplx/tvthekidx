# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

from . import online
from . utility import verbose, normalize_string, generate_oid

import sqlite3
from sqlite3 import Error
import traceback

import re

DEFAULT_MOVIE_REGEX = r'(?P<name>.*) \((?P<year>[0-9]{4})\)(?:.*?\{(?P<tvstation>[^}]+)\})?.*\..+'
DEFAULT_TVSHOW_REGEX = r'(?P<name>.*) \((?P<year>[0-9]{4})\) [Ss](?P<season>[0-9]+)[Ee](?P<episode>[0-9]+)(?:.*?\{(?P<tvstation>[^}]+)\})?.*\..+'


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------

def cleanup_orphan_tvshows(db):
    """Remove tvshow rows (+ seasons, episodes, cast, crew, genres, poster) that have no files."""
    cur = execute_sql(db,
                      "SELECT id FROM tvshows WHERE id NOT IN "
                      "(SELECT DISTINCT tvshow_id FROM files WHERE tvshow_id IS NOT NULL)")
    orphan_ids = [row['id'] for row in cur.fetchall()]
    if not orphan_ids:
        return 0
    verbose(f"Removing {len(orphan_ids)} orphaned TV show(s)...", 2)
    for sid in orphan_ids:
        execute_sql(db, "DELETE FROM actors_tvshows WHERE s_id = ?", (sid,))
        execute_sql(db, "DELETE FROM crew_tvshows WHERE s_id = ?", (sid,))
        execute_sql(db, "DELETE FROM tvshows_genres WHERE tvshow_id = ?", (sid,))
        execute_sql(db, "DELETE FROM episodes WHERE tvshow_id = ?", (sid,))
        execute_sql(db, "DELETE FROM seasons WHERE tvshow_id = ?", (sid,))
        execute_sql(db, "DELETE FROM attachments WHERE type = 'tvshow_poster' AND ref_id = ?", (sid,))
        execute_sql(db, "DELETE FROM tvshows WHERE id = ?", (sid,))
    db.commit()
    return len(orphan_ids)


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

    verbose("Removing duplicate tvshows...", 3)
    SQL = "SELECT tmdb_id FROM tvshows WHERE tmdb_id IS NOT NULL GROUP BY tmdb_id HAVING COUNT(*)>1 ORDER BY tmdb_id"
    cur = execute_sql(db, SQL)
    entries = cur.fetchall()
    for e in entries:
        tmdbid = e['tmdb_id']
        SQL = "SELECT id FROM tvshows WHERE tmdb_id = ?"
        cur = execute_sql(db, SQL, (tmdbid, ))
        entry = cur.fetchone()
        master = entry['id']
        obsolete = cur.fetchall()
        for o in obsolete:
            execute_sql(db, "UPDATE actors_tvshows SET s_id = ? WHERE s_id = ?", (master, o['id']))
            execute_sql(db, "UPDATE crew_tvshows SET s_id = ? WHERE s_id = ?", (master, o['id']))
            execute_sql(db, "UPDATE episodes SET tvshow_id = ? WHERE tvshow_id = ?", (master, o['id']))
            execute_sql(db, "UPDATE seasons SET tvshow_id = ? WHERE tvshow_id = ?", (master, o['id']))
            execute_sql(db, "DELETE FROM tvshows WHERE id = ?", (o['id'], ))

    cleanup_orphan_tvshows(db)

    verbose("Optimizing database...", 2)
    db.commit()
    SQL = "VACUUM"
    execute_sql(db, SQL)

    return True


def reset_error_counters(db):
    execute_sql(db, "UPDATE movies SET cast_error_count = 0, genre_error_count = 0", None, True)
    execute_sql(db, "UPDATE tvshows SET cast_error_count = 0, genre_error_count = 0, season_error_count = 0", None, True)
    execute_sql(db, "UPDATE files SET scan_error_count = 0", None, True)
    verbose("Error counters reset", 1)


def clear_screenshots(db):
    cur = db.cursor()
    cur.execute("DELETE FROM attachments WHERE type = 'screenshot'")
    db.commit()


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

def get_collection(db, name):
    cur = db.cursor()
    cur.execute("SELECT * FROM collections WHERE name = ?", (name,))
    return cur.fetchone()


def create_or_get_collection(db, name):
    cur = db.cursor()
    cur.execute("SELECT id FROM collections WHERE name = ?", (name,))
    row = cur.fetchone()
    if row is not None:
        return row['id'], False
    guid = generate_oid("collection", name)
    cur.execute("INSERT INTO collections (guid, name) VALUES (?, ?)", (guid, name))
    db.commit()
    return cur.lastrowid, True


def set_collection_regex(db, name, movie_regex=None, tvshow_regex=None):
    if movie_regex is not None:
        execute_sql(db, "UPDATE collections SET movie_filename_regex = ? WHERE name = ?", (movie_regex, name), True)
    if tvshow_regex is not None:
        execute_sql(db, "UPDATE collections SET tvshow_filename_regex = ? WHERE name = ?", (tvshow_regex, name), True)


# ---------------------------------------------------------------------------
# Files & Attachments
# ---------------------------------------------------------------------------

def addFileToDb(db, collection_id, filename, relpath, libtype=None):
    oid = generate_oid("file", f"{collection_id}:{relpath}:{filename}")
    insertSQL = "INSERT INTO files (collection_id, filename, relpath, movie_id, lastseen, libtype, oid) VALUES (?, ?, ?, NULL, cast(strftime('%s','now') as int), ?, ?)"
    selectSQL = "SELECT * FROM files WHERE collection_id = ? AND filename = ? AND relpath = ?"
    cur = execute_sql(db, selectSQL, (collection_id, filename, relpath))
    entry = cur.fetchone()
    if entry is None:
        execute_sql(db, insertSQL, (collection_id, filename, relpath, libtype, oid))
        return True
    if libtype and entry['libtype'] is None:
        execute_sql(db, "UPDATE files SET libtype = ? WHERE id = ?", (libtype, entry['id']))
    return entry


def updateLastSeen(db, collection_id, filename, relpath):
    execute_sql(db, "UPDATE files SET lastseen = cast(strftime('%s','now') as int) WHERE collection_id = ? AND filename = ? AND relpath = ?", (collection_id, filename, relpath))


def get_file_id(db, collection_id, filename, relpath):
    cur = db.cursor()
    cur.execute("SELECT id FROM files WHERE collection_id = ? AND filename = ? AND relpath = ?", (collection_id, filename, relpath))
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


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------

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


def getActors(db, where=None, orderby="popularity DESC, name ASC", params=None):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT a.* FROM actors a"
    if where:
        selectSQL = f"{selectSQL} JOIN actors_movies am ON am.a_id=a.id JOIN movies m ON am.m_id=m.id JOIN files f ON f.movie_id = m.id WHERE {where}"
        selectSQL = f"{selectSQL} UNION SELECT DISTINCT a.* FROM actors a"
        selectSQL = f"{selectSQL} JOIN crew_movies cm ON cm.a_id=a.id JOIN movies m ON cm.m_id=m.id JOIN files f ON f.movie_id = m.id WHERE {where}"
        selectSQL = f"{selectSQL} UNION SELECT DISTINCT a.* FROM actors a"
        selectSQL = f"{selectSQL} JOIN actors_tvshows ats ON ats.a_id=a.id JOIN tvshows s ON ats.s_id=s.id JOIN files f ON f.tvshow_id=s.id WHERE {where}"
        selectSQL = f"{selectSQL} UNION SELECT DISTINCT a.* FROM actors a"
        selectSQL = f"{selectSQL} JOIN crew_tvshows cts ON cts.a_id=a.id JOIN tvshows s ON cts.s_id=s.id JOIN files f ON f.tvshow_id=s.id WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    all_params = (list(params) * 4) if params else []
    cur.execute(selectSQL, all_params)
    return cur.fetchall()


def getCast(db, mid, limit=None):
    cur = db.cursor()
    selectSQL = "SELECT a.* FROM actors_movies c JOIN actors a ON c.a_id = a.id JOIN movies m ON c.m_id = m.id WHERE m.id = ? ORDER BY a.popularity DESC"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


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


# ---------------------------------------------------------------------------
# Genres
# ---------------------------------------------------------------------------

def addGenreToDb(db, tmdb_id, name):
    cur = execute_sql(db, "SELECT id FROM genres WHERE tmdb_id = ?", (tmdb_id,))
    row = cur.fetchone()
    if row is None:
        oid = generate_oid("genre", str(tmdb_id))
        result = execute_sql(db, "INSERT INTO genres(tmdb_id, name, oid) VALUES (?, ?, ?)", (tmdb_id, name, oid))
        return result.lastrowid
    return row['id']


def addGenreToMovieDb(db, movie_id, genre_id):
    cur = execute_sql(db, "SELECT 1 FROM movies_genres WHERE movie_id = ? AND genre_id = ?", (movie_id, genre_id))
    if cur.fetchone() is None:
        execute_sql(db, "INSERT INTO movies_genres(movie_id, genre_id) VALUES (?, ?)", (movie_id, genre_id))


def addGenreToTVShowDb(db, tvshow_id, genre_id):
    cur = execute_sql(db, "SELECT 1 FROM tvshows_genres WHERE tvshow_id = ? AND genre_id = ?", (tvshow_id, genre_id))
    if cur.fetchone() is None:
        execute_sql(db, "INSERT INTO tvshows_genres(tvshow_id, genre_id) VALUES (?, ?)", (tvshow_id, genre_id))


def storeMovieGenres(db, movie_id, genres):
    for genre in genres:
        gid = addGenreToDb(db, genre['id'], genre['name'])
        addGenreToMovieDb(db, movie_id, gid)
    db.commit()


def getGenres_bulk(db, movie_ids):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT g.id, g.oid, g.name, g.tmdb_id, mg.movie_id FROM movies_genres mg JOIN genres g ON mg.genre_id = g.id WHERE mg.movie_id IN ({ph}) ORDER BY g.name ASC",
        list(movie_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["movie_id"], []).append(row)
    return result


def getTVGenres_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT g.id, g.oid, g.name, g.tmdb_id, tg.tvshow_id "
        f"FROM tvshows_genres tg JOIN genres g ON tg.genre_id = g.id "
        f"WHERE tg.tvshow_id IN ({ph}) ORDER BY g.name ASC",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["tvshow_id"], []).append(row)
    return result


# ---------------------------------------------------------------------------
# Movies
# ---------------------------------------------------------------------------

def addMovieToDb(db, movie):
    key = str(movie['tmdb_id']) if movie['tmdb_id'] else f"{movie['title']}:{movie['release_year']}"
    oid = generate_oid("movie", key)
    insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, title_normalized, year, description, popularity, score, oid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    result = execute_sql(db, insertSQL, (movie['tmdb_id'], movie['title'], movie['orig_title'], normalize_string(movie['title']), movie['release_year'], movie['description'], movie['popularity'], movie['score'], oid))
    movie_id = result.lastrowid
    if movie.get('poster'):
        add_movie_attachment(db, movie_id, 'poster', movie['poster'])
    return movie_id


def lookupMovie(db, search, title, year):
    verbose("Lookup movie: " + title, 2)
    cur = execute_sql(db, "SELECT id FROM movies WHERE title=? AND year=?", (title, year))
    entry = cur.fetchone()
    if entry is not None:
        return entry['id']

    result = online.query_movie(search, title, year)
    if result is not None:
        # Guard: movie may already exist under a different title but same TMDB ID
        existing = execute_sql(db, "SELECT id FROM movies WHERE tmdb_id=?", (result['id'],)).fetchone()
        if existing:
            return existing['id']
        try:
            poster = online.fetchPoster(result['poster_path'])
        except Exception as e:
            verbose(f"Failed to fetch poster for '{title}': {e}", 1)
            poster = None
        movie = {
            "tmdb_id": result['id'],
            "title": result['title'],
            "orig_title": result['original_title'],
            "release_year": result['release_date'][0:4],
            "description": result['overview'] if result['overview'] else None,
            "popularity": result['popularity'],
            "score": result['vote_average'] * 10,
            "poster": poster,
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


def assignMovieToFile(db, fid, mid):
    cur = db.cursor()
    updateSQL = "UPDATE files SET movie_id = ? WHERE id = ?"
    cur.execute(updateSQL, (mid, fid))
    return True


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


def getMovies(db, where=None, orderby=None, limit=None, params=None):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT m.* FROM movies m JOIN files f ON m.id=f.movie_id"
    if where:
        selectSQL = f"{selectSQL} WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, list(params) if params else [])
    return cur.fetchall()


def getCollections(db, mid):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT f.id, c.name AS collection, f.filename, f.size, f.added, f.ctime, f.codec, f.width, f.height, f.duration, f.tvstation FROM files f LEFT JOIN collections c ON f.collection_id = c.id WHERE f.movie_id = ? ORDER BY c.name ASC"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getCollections_bulk(db, movie_ids):
    if not movie_ids:
        return {}
    ph = ",".join("?" * len(movie_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT DISTINCT f.id, c.name AS collection, f.filename, f.size, f.added, f.ctime, f.codec, f.width, f.height, f.duration, f.tvstation, f.movie_id FROM files f LEFT JOIN collections c ON f.collection_id = c.id WHERE f.movie_id IN ({ph}) ORDER BY c.name ASC",
        list(movie_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["movie_id"], []).append(row)
    return result


def scanMovies(db, search):
    selectSQL = (
        "SELECT f.id, f.filename, c.movie_filename_regex FROM files f "
        "LEFT JOIN collections c ON f.collection_id = c.id "
        "WHERE (f.movie_id IS NULL OR f.movie_id=0) AND (f.episode_id IS NULL) AND (f.libtype = 'movies') "
        "ORDER BY f.filename ASC"
    )
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        pattern = row['movie_filename_regex'] or DEFAULT_MOVIE_REGEX
        m = re.search(pattern, row['filename'])
        if not m:
            verbose(f"No movies regex match: {row['filename']}", 2)
            continue
        basename = m.group('name')
        year = int(m.group('year'))
        try:
            m_id = lookupMovie(db, search, basename, year)
            assignMovieToFile(db, row['id'], m_id)
            try:
                station = m.group('tvstation')
                if station:
                    db.cursor().execute(
                        "UPDATE files SET tvstation = ? WHERE id = ? AND tvstation IS NULL",
                        (station.lower(), row['id']))
            except IndexError:
                pass
            db.commit()
        except Exception as e:
            verbose(f"Error processing movie file '{row['filename']}': {e}", 1)
            verbose(traceback.format_exc(), 2)
    return None


def scanMovieCredits(db, movie_api):
    verbose("Scanning for cast and crew...", 2)
    selectSQL = "SELECT id, title, tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND cast_error_count < 3 AND NOT (id IN (SELECT DISTINCT m_id FROM actors_movies UNION SELECT DISTINCT m_id FROM crew_movies)) ORDER BY title ASC"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        verbose("Lookup cast for " + row['title'], 2)
        try:
            cast, crew = online.query_cast(movie_api, row['tmdb_id'])
        except Exception as e:
            execute_sql(db, "UPDATE movies SET cast_error_count = cast_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"Error fetching cast for '{row['title']}': {e}", 1)
            db.commit()
            continue
        if not cast and not crew:
            execute_sql(db, "UPDATE movies SET cast_error_count = cast_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"No cast returned for {row['title']}, error count incremented", 2)
        else:
            for person in cast:
                aid = addActorToDb(db, person)
                addActorToMovieDb(db, row['id'], aid)
            for person in crew:
                aid = addActorToDb(db, person)
                addCrewToMovieDb(db, row['id'], aid, person['job'])
        db.commit()
    return None


def scanMovieGenres(db, movie_api, limit=None):
    verbose("Scanning for genres...", 2)
    sql = "SELECT id, tmdb_id, title FROM movies WHERE tmdb_id IS NOT NULL AND genre_error_count < 3 AND id NOT IN (SELECT DISTINCT movie_id FROM movies_genres) ORDER BY title ASC"
    if limit:
        sql += f" LIMIT {limit}"
    cur = execute_sql(db, sql)
    for row in cur.fetchall():
        verbose(f"Fetching genres for {row['title']}", 2)
        try:
            genres = online.query_genres(movie_api, row['tmdb_id'])
        except Exception as e:
            execute_sql(db, "UPDATE movies SET genre_error_count = genre_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"Error fetching genres for '{row['title']}': {e}", 1)
            continue
        if genres:
            storeMovieGenres(db, row['id'], genres)
        else:
            execute_sql(db, "UPDATE movies SET genre_error_count = genre_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"No genres returned for {row['title']}, error count incremented", 2)


def refresh_movie(db, movie_api, tmdbid):
    cur = execute_sql(db, "SELECT id FROM movies WHERE tmdb_id = ?", (tmdbid,))
    row = cur.fetchone()
    if row is None:
        verbose(f"Movie with TMDB ID {tmdbid} not found in database", 1)
        return False
    mid = row['id']

    result = online.query_movie_by_id(movie_api, tmdbid)
    if result is None:
        verbose(f"Could not fetch TMDB data for ID {tmdbid}", 1)
        return False

    release_year = result['release_date'][0:4] if result.get('release_date') else None
    execute_sql(db,
                "UPDATE movies SET title=?, title_orig=?, title_normalized=?, year=?, description=?, popularity=?, score=? WHERE id=?",
                (result['title'], result['original_title'], normalize_string(result['title']),
                 release_year, result['overview'] or None,
                 result['popularity'], result['vote_average'] * 10, mid))
    cur2 = execute_sql(db, "SELECT oid FROM movies WHERE id = ?", (mid,))
    if cur2.fetchone()['oid'] is None:
        execute_sql(db, "UPDATE movies SET oid = ? WHERE id = ?",
                    (generate_oid("movie", str(tmdbid)), mid))

    poster_path = result.get('poster_path')
    verbose(f"Poster path from TMDB: {poster_path}", 2)
    poster_data = None
    if poster_path:
        try:
            poster_data = online.fetchPoster(poster_path)
        except Exception as e:
            verbose(f"Failed to fetch poster: {e}", 1)
    if poster_data:
        db.cursor().execute("DELETE FROM attachments WHERE ref_id = ? AND type = 'poster'", (mid,))
        add_movie_attachment(db, mid, 'poster', poster_data)
    else:
        verbose("No poster available for this movie", 2)

    execute_sql(db, "DELETE FROM movies_genres WHERE movie_id = ?", (mid,))
    genres = online.query_genres(movie_api, tmdbid)
    storeMovieGenres(db, mid, genres)

    cast, crew = online.query_cast(movie_api, tmdbid)

    execute_sql(db, "DELETE FROM actors_movies WHERE m_id = ?", (mid,))
    execute_sql(db, "DELETE FROM crew_movies WHERE m_id = ?", (mid,))

    for person in cast:
        aid = addActorToDb(db, person)
        execute_sql(db, "UPDATE actors SET name=?, popularity=? WHERE id=?",
                    (person['name'], person['popularity'], aid))
        if person.get('profile'):
            db.cursor().execute("DELETE FROM attachments WHERE ref_id = ? AND type = 'profile'", (aid,))
            add_actor_attachment(db, aid, 'profile', person['profile'])
        addActorToMovieDb(db, mid, aid)

    for person in crew:
        aid = addActorToDb(db, person)
        execute_sql(db, "UPDATE actors SET name=?, popularity=? WHERE id=?",
                    (person['name'], person['popularity'], aid))
        if person.get('profile'):
            db.cursor().execute("DELETE FROM attachments WHERE ref_id = ? AND type = 'profile'", (aid,))
            add_actor_attachment(db, aid, 'profile', person['profile'])
        addCrewToMovieDb(db, mid, aid, person['job'])

    execute_sql(db, "UPDATE movies SET refresh_timestamp = cast(strftime('%s','now') as int) WHERE id = ?", (mid,))
    db.commit()
    verbose(f"Movie {tmdbid} refreshed", 1)
    return True


def refresh_movies_bulk(db, movie_api):
    cur = db.cursor()
    month_ago = "refresh_timestamp IS NULL OR refresh_timestamp < cast(strftime('%s','now') as int) - 2592000"

    cur.execute(f"SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY score DESC LIMIT 10")
    top = [r['tmdb_id'] for r in cur.fetchall()]

    cur.execute(f"SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY RANDOM() LIMIT 10")
    rnd = [r['tmdb_id'] for r in cur.fetchall()]

    cur.execute(f"SELECT tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY refresh_timestamp ASC LIMIT 10")
    oldest = [r['tmdb_id'] for r in cur.fetchall()]

    seen = set()
    candidates = []
    for tmdbid in top + rnd + oldest:
        if tmdbid not in seen:
            seen.add(tmdbid)
            candidates.append(tmdbid)

    verbose(f"Refreshing {len(candidates)} movies...", 1)
    for tmdbid in candidates:
        try:
            refresh_movie(db, movie_api, tmdbid)
        except Exception as e:
            verbose(f"Error refreshing movie {tmdbid}: {e}", 1)


# ---------------------------------------------------------------------------
# TV Shows
# ---------------------------------------------------------------------------

def addTVShowToDb(db, show):
    if show['tmdb_id'] is not None:
        existing = execute_sql(db, "SELECT id FROM tvshows WHERE tmdb_id = ?", (show['tmdb_id'],)).fetchone()
        if existing:
            return existing['id']
    key = str(show['tmdb_id']) if show['tmdb_id'] else f"{show['title']}:{show['year']}"
    oid = generate_oid("tvshow", key)
    result = execute_sql(db,
                         "INSERT INTO tvshows(tmdb_id, title, title_orig, title_normalized, year, description, popularity, score, oid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (show['tmdb_id'], show['title'], show['orig_title'], normalize_string(show['title']),
                          show['year'], show.get('description'), show.get('popularity', 0), show.get('score', 0), oid))
    show_id = result.lastrowid
    if show.get('poster'):
        add_tvshow_attachment(db, show_id, 'tvshow_poster', show['poster'])
    return show_id


def addSeasonToDb(db, tvshow_id, tvshow_tmdb_id, season_number, title, year):
    oid = generate_oid("season", f"{tvshow_tmdb_id}:{season_number}")
    execute_sql(db,
                "INSERT OR IGNORE INTO seasons(tvshow_id, season_number, title, year, oid) VALUES (?, ?, ?, ?, ?)",
                (tvshow_id, season_number, title, year, oid))
    cur = execute_sql(db, "SELECT id FROM seasons WHERE tvshow_id = ? AND season_number = ?", (tvshow_id, season_number))
    return cur.fetchone()['id']


def addEpisodeToDb(db, episode):
    oid = generate_oid("episode", f"{episode['tvshow_tmdb_id']}:{episode['season_number']}:{episode['episode_number']}")
    execute_sql(db,
                "INSERT OR IGNORE INTO episodes(tvshow_id, season_id, season_number, episode_number, title, year, description, score, oid) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (episode['tvshow_id'], episode['season_id'], episode['season_number'],
                 episode['episode_number'], episode.get('title'), episode.get('year'),
                 episode.get('description'), episode.get('score', 0), oid))
    cur = execute_sql(db, "SELECT id FROM episodes WHERE tvshow_id = ? AND season_number = ? AND episode_number = ?",
                      (episode['tvshow_id'], episode['season_number'], episode['episode_number']))
    return cur.fetchone()['id']


def _fetch_show_episodes(db, tv, show_id, tmdb_id, details):
    seasons_data = details.get('seasons', [])
    if seasons_data is None:
        return
    for season_info in seasons_data:
        sn = int(season_info['season_number'])
        if sn == 0:
            continue
        season_title = str(season_info.get('name') or '') or None
        season_air = season_info.get('air_date') or ''
        season_year = int(season_air[:4]) if len(season_air) >= 4 else None
        season_id = addSeasonToDb(db, show_id, tmdb_id, sn, season_title, season_year)
        try:
            episodes = online.query_tvshow_season(tv, tmdb_id, sn)
        except Exception as e:
            execute_sql(db, "UPDATE tvshows SET season_error_count = season_error_count + 1 WHERE id = ?", (show_id,), True)
            verbose(f"Failed to fetch season {sn} for show {tmdb_id}: {e}", 1)
            continue
        for ep in episodes:
            addEpisodeToDb(db, {
                "tvshow_id": show_id,
                "tvshow_tmdb_id": tmdb_id,
                "season_id": season_id,
                "season_number": sn,
                "episode_number": ep['episode_number'],
                "title": ep.get('title'),
                "year": ep.get('year'),
                "description": ep.get('description'),
                "score": ep.get('score', 0),
            })
        db.commit()


def lookupTVShow(db, search, tv, title, year, episode_tag=None):
    verbose(f"Lookup TV show: {title}{(' ' + episode_tag) if episode_tag else ''}", 2)
    # Look up by title only — year in filenames is unreliable for multi-season shows
    cur = execute_sql(db, "SELECT id, tmdb_id FROM tvshows WHERE title = ? ORDER BY id LIMIT 1", (title,))
    entry = cur.fetchone()
    if entry:
        show_id = entry['id']
        tmdb_id = entry['tmdb_id']
        ep_count = execute_sql(db, "SELECT COUNT(*) FROM episodes WHERE tvshow_id = ?", (show_id,)).fetchone()[0]
        if ep_count > 0 and tmdb_id is not None:
            return show_id
        # tmdb_id is NULL (previous TMDB search failed) — retry the search now.
        if tmdb_id is None:
            result = online.query_tvshow(search, title, year)
            if result is not None:
                tmdb_id = result['id']
        if tmdb_id is not None:
            details = online.query_tvshow_by_id(tv, tmdb_id)
            if details:
                new_oid = generate_oid("tvshow", str(tmdb_id))
                execute_sql(db,
                            "UPDATE tvshows SET tmdb_id=?, title_orig=?, title_normalized=?, description=?, popularity=?, score=?, oid=? WHERE id=?",
                            (tmdb_id, details.get('original_name', title), normalize_string(title),
                             details.get('overview') or None, details.get('popularity', 0),
                             float(details.get('vote_average') or 0) * 10, new_oid, show_id), True)
                poster = online.fetchPoster(details.get('poster_path'))
                if poster:
                    add_tvshow_attachment(db, show_id, 'tvshow_poster', poster)
                verbose(f"Re-fetching episodes for {title} (none in DB)", 2)
                _fetch_show_episodes(db, tv, show_id, tmdb_id, details)
        return show_id

    result = online.query_tvshow(search, title, year)
    if result is None:
        verbose(f"Cannot find TV show online: {title}", 1)
        stub = {
            "tmdb_id": None, "title": title, "orig_title": title,
            "year": year, "description": None, "popularity": 0, "score": 0, "poster": None,
        }
        return addTVShowToDb(db, stub)

    tmdb_id = result['id']
    # Guard: same tmdb_id may already exist under a different title or year
    existing = execute_sql(db, "SELECT id FROM tvshows WHERE tmdb_id = ?", (tmdb_id,)).fetchone()
    if existing:
        show_id = existing['id']
        ep_count = execute_sql(db, "SELECT COUNT(*) FROM episodes WHERE tvshow_id = ?", (show_id,)).fetchone()[0]
        if ep_count == 0:
            details_retry = online.query_tvshow_by_id(tv, tmdb_id)
            if details_retry:
                _fetch_show_episodes(db, tv, show_id, tmdb_id, details_retry)
        return show_id

    details = online.query_tvshow_by_id(tv, tmdb_id)
    if details is None:
        stub = {
            "tmdb_id": tmdb_id, "title": title, "orig_title": title,
            "year": year, "description": None, "popularity": 0, "score": 0, "poster": None,
        }
        return addTVShowToDb(db, stub)

    first_air = details.get('first_air_date') or ''
    show_year = int(first_air[:4]) if len(first_air) >= 4 else year
    try:
        poster = online.fetchPoster(details.get('poster_path'))
    except Exception as e:
        verbose(f"Failed to fetch poster for TV show '{title}': {e}", 1)
        poster = None
    show = {
        "tmdb_id": tmdb_id,
        "title": details.get('name', title),
        "orig_title": details.get('original_name', title),
        "year": show_year,
        "description": details.get('overview') or None,
        "popularity": details.get('popularity', 0),
        "score": float(details.get('vote_average') or 0) * 10,
        "poster": poster,
    }
    show_id = addTVShowToDb(db, show)
    _fetch_show_episodes(db, tv, show_id, tmdb_id, details)
    return show_id


def addActorToTVShowDb(db, show_id, actor_id):
    cur = execute_sql(db, "SELECT 1 FROM actors_tvshows WHERE a_id = ? AND s_id = ?", (actor_id, show_id))
    if cur.fetchone() is None:
        execute_sql(db, "INSERT INTO actors_tvshows(a_id, s_id) VALUES (?, ?)", (actor_id, show_id))


def addCrewToTVShowDb(db, show_id, actor_id, job):
    cur = execute_sql(db, "SELECT 1 FROM crew_tvshows WHERE a_id = ? AND s_id = ?", (actor_id, show_id))
    if cur.fetchone() is None:
        execute_sql(db, "INSERT INTO crew_tvshows(a_id, s_id, job) VALUES (?, ?, ?)", (actor_id, show_id, job))


def assignEpisodeToFile(db, fid, eid):
    execute_sql(db,
                "UPDATE files SET episode_id = ?, "
                "tvshow_id = (SELECT tvshow_id FROM episodes WHERE id = ?) "
                "WHERE id = ?",
                (eid, eid, fid), True)


def add_tvshow_attachment(db, tvshow_id, att_type, data):
    cur = db.cursor()
    cur.execute("INSERT INTO attachments (type, data, ref_id) VALUES (?, ?, ?)", (att_type, sqlite3.Binary(data), tvshow_id))
    db.commit()


def get_tvshow_attachments(db, tvshow_id, att_type=None):
    sql = "SELECT id, type, data FROM attachments WHERE ref_id = ?"
    params = (tvshow_id,)
    if att_type:
        sql += " AND type = ?"
        params = (tvshow_id, att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    return cur.fetchall()


def get_tvshow_attachments_bulk(db, tvshow_ids, att_type=None):
    if not tvshow_ids:
        return {}
    ph = ",".join("?" * len(tvshow_ids))
    sql = f"SELECT id, type, data, ref_id FROM attachments WHERE ref_id IN ({ph})"
    params = list(tvshow_ids)
    if att_type:
        sql += " AND type = ?"
        params.append(att_type)
    cur = db.cursor()
    cur.execute(sql, params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["ref_id"], []).append(row)
    return result


def getTVShows(db, where=None, orderby=None, limit=None, params=None):
    cur = db.cursor()
    # Join via tvshow_id (set for all TV show files, matched or not) so that
    # shows with only unmatched-episode files are included.
    selectSQL = (
        "SELECT DISTINCT s.* FROM tvshows s "
        "JOIN files f ON f.tvshow_id = s.id"
    )
    if where:
        selectSQL = f"{selectSQL} WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, list(params) if params else [])
    return cur.fetchall()


def getTVSeasons_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT * FROM seasons WHERE tvshow_id IN ({ph}) ORDER BY tvshow_id, season_number",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["tvshow_id"], []).append(row)
    return result


def getEpisodes_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT * FROM episodes WHERE tvshow_id IN ({ph}) ORDER BY tvshow_id, season_number, episode_number",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["tvshow_id"], []).append(row)
    return result


def getEpisodeFiles_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT f.*, e.tvshow_id FROM files f "
        f"JOIN episodes e ON f.episode_id = e.id "
        f"WHERE e.tvshow_id IN ({ph})",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["episode_id"], []).append(row)
    return result


def getUnmatchedEpisodeFiles_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT f.* FROM files f "
        f"WHERE f.tvshow_id IN ({ph}) AND f.episode_id IS NULL AND f.libtype = 'tvshows' "
        f"ORDER BY f.tvshow_id, f.filename",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["tvshow_id"], []).append(row)
    return result


def getTVCast_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT a.*, ats.s_id FROM actors a "
        f"JOIN actors_tvshows ats ON ats.a_id = a.id "
        f"WHERE ats.s_id IN ({ph}) "
        f"ORDER BY a.popularity DESC",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["s_id"], []).append(row)
    return result


def getTVCrew_bulk(db, show_ids):
    if not show_ids:
        return {}
    ph = ",".join("?" * len(show_ids))
    cur = db.cursor()
    cur.execute(
        f"SELECT a.*, cts.s_id, cts.job FROM actors a "
        f"JOIN crew_tvshows cts ON cts.a_id = a.id "
        f"WHERE cts.s_id IN ({ph}) "
        f"ORDER BY a.popularity DESC",
        list(show_ids))
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["s_id"], []).append(row)
    return result


def getTVShowsByActor_bulk(db, actor_ids):
    if not actor_ids:
        return {}
    ph = ",".join("?" * len(actor_ids))
    params = list(actor_ids)
    sql = (
        f"SELECT s.id, s.oid, s.title, s.title_normalized, s.score, s.year, ats.a_id "
        f"FROM actors_tvshows ats JOIN tvshows s ON ats.s_id = s.id WHERE ats.a_id IN ({ph}) "
        f"UNION "
        f"SELECT s.id, s.oid, s.title, s.title_normalized, s.score, s.year, cts.a_id "
        f"FROM crew_tvshows cts JOIN tvshows s ON cts.s_id = s.id WHERE cts.a_id IN ({ph}) "
        f"ORDER BY s.title_normalized COLLATE NOCASE ASC, s.year ASC"
    )
    cur = db.cursor()
    cur.execute(sql, params + params)
    result = {}
    for row in cur.fetchall():
        result.setdefault(row["a_id"], []).append(row)
    return result


def scanTVShows(db, search, tv):
    verbose("Scanning TV shows...", 2)
    selectSQL = (
        "SELECT f.id, f.filename, c.tvshow_filename_regex "
        "FROM files f LEFT JOIN collections c ON f.collection_id = c.id "
        "WHERE (f.episode_id IS NULL) AND (f.movie_id IS NULL) AND (f.libtype = 'tvshows') "
        "AND (f.scan_error_count IS NULL OR f.scan_error_count < 3) "
        "ORDER BY f.filename ASC"
    )
    cur = execute_sql(db, selectSQL)
    show_id_cache = {}
    season_fetch_attempted = set()  # (show_id, season_number) — skip repeat fetches
    for row in cur.fetchall():
        pattern = row['tvshow_filename_regex'] or DEFAULT_TVSHOW_REGEX
        m = re.search(pattern, row['filename'])
        if not m:
            verbose(f"No TV show regex match: {row['filename']}", 2)
            continue
        try:
            name = m.group('name')
            year = int(m.group('year'))
            season_number = int(m.group('season'))
            episode_number = int(m.group('episode'))
        except (IndexError, ValueError):
            verbose(f"Regex group missing for: {row['filename']}", 2)
            continue

        episode_tag = f"S{season_number:02d}E{episode_number:02d}"
        try:
            station = m.group('tvstation')
        except IndexError:
            station = None
        if station:
            execute_sql(db,
                        "UPDATE files SET tvstation = ? WHERE id = ? AND tvstation IS NULL",
                        (station.lower(), row['id']), True)
        try:
            if name in show_id_cache:
                show_id = show_id_cache[name]
                verbose(f"Lookup TV show: {name} {episode_tag} (cached)", 2)
            else:
                show_id = lookupTVShow(db, search, tv, name, year, episode_tag)
                show_id_cache[name] = show_id
            execute_sql(db, "UPDATE files SET tvshow_id = ? WHERE id = ?", (show_id, row['id']), True)

            ep_cur = execute_sql(db,
                                 "SELECT id FROM episodes WHERE tvshow_id = ? AND season_number = ? AND episode_number = ?",
                                 (show_id, season_number, episode_number))
            ep_entry = ep_cur.fetchone()
            if ep_entry is None:
                # Episode missing — season may never have been fetched (partial failure or first run).
                # Fetch this specific season now, but only once per (show, season) per scan run.
                season_key = (show_id, season_number)
                show_row = execute_sql(db, "SELECT tmdb_id FROM tvshows WHERE id = ?", (show_id,)).fetchone()
                if show_row and show_row['tmdb_id'] and season_key not in season_fetch_attempted:
                    season_fetch_attempted.add(season_key)
                    tmdb_id = show_row['tmdb_id']
                    season_row = execute_sql(db,
                                             "SELECT id FROM seasons WHERE tvshow_id = ? AND season_number = ?",
                                             (show_id, season_number)).fetchone()
                    season_id = season_row['id'] if season_row else addSeasonToDb(db, show_id, tmdb_id, season_number, None, None)
                    verbose(f"Fetching season {season_number} for {name}", 2)
                    try:
                        episodes = online.query_tvshow_season(tv, tmdb_id, season_number)
                    except Exception as e:
                        verbose(f"Error fetching season {season_number} for '{name}': {e}", 1)
                        episodes = []
                    for ep in episodes:
                        addEpisodeToDb(db, {
                            "tvshow_id": show_id,
                            "tvshow_tmdb_id": tmdb_id,
                            "season_id": season_id,
                            "season_number": season_number,
                            "episode_number": ep['episode_number'],
                            "title": ep.get('title'),
                            "year": ep.get('year'),
                            "description": ep.get('description'),
                            "score": ep.get('score', 0),
                        })
                    db.commit()
                    ep_cur = execute_sql(db,
                                         "SELECT id FROM episodes WHERE tvshow_id = ? AND season_number = ? AND episode_number = ?",
                                         (show_id, season_number, episode_number))
                    ep_entry = ep_cur.fetchone()
            if ep_entry:
                assignEpisodeToFile(db, row['id'], ep_entry['id'])
            else:
                season_ep_count = execute_sql(db,
                                              "SELECT COUNT(*) FROM episodes WHERE tvshow_id = ? AND season_number = ?",
                                              (show_id, season_number)).fetchone()[0]
                if season_ep_count > 0:
                    execute_sql(db, "UPDATE files SET scan_error_count = scan_error_count + 1 WHERE id = ?", (row['id'],), True)
                    verbose(f"S{season_number:02d}E{episode_number:02d} not on TMDB (season has {season_ep_count} episodes): {row['filename']}", 1)
                else:
                    verbose(f"S{season_number:02d}E{episode_number:02d} not linked — season fetch failed: {row['filename']}", 1)
            db.commit()
        except Exception as e:
            verbose(f"Error processing TV show file '{row['filename']}': {e}", 1)
            verbose(traceback.format_exc(), 2)


def scanTVCredits(db, tv):
    verbose("Scanning for TV show cast and crew...", 2)
    selectSQL = (
        "SELECT s.id, s.title, s.tmdb_id FROM tvshows s "
        "WHERE s.tmdb_id IS NOT NULL AND s.cast_error_count < 3 "
        "AND s.id NOT IN (SELECT DISTINCT s_id FROM actors_tvshows UNION SELECT DISTINCT s_id FROM crew_tvshows) "
        "ORDER BY s.title ASC"
    )
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        verbose(f"Lookup cast for TV show: {row['title']}", 2)
        try:
            cast, crew = online.query_tvshow_credits(tv, row['tmdb_id'])
        except Exception as e:
            execute_sql(db, "UPDATE tvshows SET cast_error_count = cast_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"Error fetching cast for TV show '{row['title']}': {e}", 1)
            db.commit()
            continue
        if not cast and not crew:
            execute_sql(db, "UPDATE tvshows SET cast_error_count = cast_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"No cast returned for TV show {row['title']}, error count incremented", 2)
        else:
            for person in cast:
                aid = addActorToDb(db, person)
                addActorToTVShowDb(db, row['id'], aid)
            for person in crew:
                aid = addActorToDb(db, person)
                addCrewToTVShowDb(db, row['id'], aid, person.get('job', ''))
        db.commit()


def scanTVGenres(db, tv):
    verbose("Scanning for TV show genres...", 2)
    sql = (
        "SELECT s.id, s.tmdb_id, s.title FROM tvshows s "
        "WHERE s.tmdb_id IS NOT NULL AND s.genre_error_count < 3 "
        "AND s.id NOT IN (SELECT DISTINCT tvshow_id FROM tvshows_genres) "
        "ORDER BY s.title ASC"
    )
    cur = execute_sql(db, sql)
    for row in cur.fetchall():
        verbose(f"Fetching genres for TV show: {row['title']}", 2)
        try:
            details = online.query_tvshow_by_id(tv, row['tmdb_id'])
        except Exception as e:
            execute_sql(db, "UPDATE tvshows SET genre_error_count = genre_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"Error fetching genres for TV show '{row['title']}': {e}", 1)
            continue
        genres = [{"id": g['id'], "name": g['name']} for g in details.get('genres', [])]
        if genres:
            for genre in genres:
                gid = addGenreToDb(db, genre['id'], genre['name'])
                addGenreToTVShowDb(db, row['id'], gid)
            db.commit()
        else:
            execute_sql(db, "UPDATE tvshows SET genre_error_count = genre_error_count + 1 WHERE id = ?", (row['id'],), True)
            verbose(f"No genres returned for TV show {row['title']}, error count incremented", 2)


def refresh_tvshow(db, tv_api, tmdbid):
    cur = execute_sql(db, "SELECT id FROM tvshows WHERE tmdb_id = ?", (tmdbid,))
    row = cur.fetchone()
    if row is None:
        verbose(f"TV show with TMDB ID {tmdbid} not found in database", 1)
        return False
    show_id = row['id']

    details = online.query_tvshow_by_id(tv_api, tmdbid)
    if details is None:
        verbose(f"Could not fetch TMDB data for TV show ID {tmdbid}", 1)
        return False

    first_air = details.get('first_air_date') or ''
    year = int(first_air[:4]) if len(first_air) >= 4 else None
    execute_sql(db,
                "UPDATE tvshows SET title=?, title_orig=?, title_normalized=?, year=?, description=?, popularity=?, score=? WHERE id=?",
                (details.get('name'), details.get('original_name'), normalize_string(details.get('name', '')),
                 year, details.get('overview') or None,
                 details.get('popularity', 0), float(details.get('vote_average') or 0) * 10, show_id))

    poster_path = details.get('poster_path')
    if poster_path:
        try:
            poster_data = online.fetchPoster(poster_path)
            if poster_data:
                db.cursor().execute("DELETE FROM attachments WHERE ref_id = ? AND type = 'tvshow_poster'", (show_id,))
                add_tvshow_attachment(db, show_id, 'tvshow_poster', poster_data)
        except Exception as e:
            verbose(f"Failed to fetch TV show poster: {e}", 1)

    execute_sql(db, "DELETE FROM tvshows_genres WHERE tvshow_id = ?", (show_id,))
    genres = [{"id": g['id'], "name": g['name']} for g in details.get('genres', [])]
    for genre in genres:
        gid = addGenreToDb(db, genre['id'], genre['name'])
        addGenreToTVShowDb(db, show_id, gid)

    cast, crew = online.query_tvshow_credits(tv_api, tmdbid)
    execute_sql(db, "DELETE FROM actors_tvshows WHERE s_id = ?", (show_id,))
    execute_sql(db, "DELETE FROM crew_tvshows WHERE s_id = ?", (show_id,))
    for person in cast:
        aid = addActorToDb(db, person)
        addActorToTVShowDb(db, show_id, aid)
    for person in crew:
        aid = addActorToDb(db, person)
        addCrewToTVShowDb(db, show_id, aid, person.get('job', ''))

    execute_sql(db, "UPDATE tvshows SET refresh_timestamp = cast(strftime('%s','now') as int) WHERE id = ?", (show_id,))
    db.commit()
    verbose(f"TV show {tmdbid} refreshed", 1)
    return True


def refresh_tvshows_bulk(db, tv_api):
    cur = db.cursor()
    month_ago = "refresh_timestamp IS NULL OR refresh_timestamp < cast(strftime('%s','now') as int) - 2592000"
    cur.execute(f"SELECT tmdb_id FROM tvshows WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY score DESC LIMIT 10")
    top = [r['tmdb_id'] for r in cur.fetchall()]
    cur.execute(f"SELECT tmdb_id FROM tvshows WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY RANDOM() LIMIT 10")
    rnd = [r['tmdb_id'] for r in cur.fetchall()]
    cur.execute(f"SELECT tmdb_id FROM tvshows WHERE tmdb_id IS NOT NULL AND ({month_ago}) ORDER BY refresh_timestamp ASC LIMIT 10")
    oldest = [r['tmdb_id'] for r in cur.fetchall()]
    seen = set()
    candidates = []
    for tmdbid in top + rnd + oldest:
        if tmdbid not in seen:
            seen.add(tmdbid)
            candidates.append(tmdbid)
    verbose(f"Refreshing {len(candidates)} TV shows...", 1)
    for tmdbid in candidates:
        try:
            refresh_tvshow(db, tv_api, tmdbid)
        except Exception as e:
            verbose(f"Error refreshing TV show {tmdbid}: {e}", 1)
