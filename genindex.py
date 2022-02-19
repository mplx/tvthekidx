#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import glob
import os
import re
import sys
import getopt

from urllib.request import urlopen

from sqlite3 import Error

from tmdbv3api import TMDb
from tmdbv3api import Movie
from tmdbv3api import Search


VERBOSITY_LEVEL = 1
UNKNOWN_IGNORE = True


def verbose(text, level=1):
    global VERBOSITY_LEVEL

    if VERBOSITY_LEVEL >= level:
        print(f"[{level}] {text}")


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
    except Error as e:
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


def cleanup_db(conn):
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
            filesUpdateSQL = "UPDATE files SET movie_id = ? WHERE movie_id = ?"
            cleanupSQL = "DELETE FROM movies WHERE id = ?"
            try:
                c = db.cursor()
                c.execute(actorsUpdateSQL, (master, o['id']))
            except Error:
                cur = execute_sql(db, actorsDeleteSQL, (o['id'], ))
            cur = execute_sql(db, filesUpdateSQL, (master, o['id']))
            cur = execute_sql(db, cleanupSQL, (o['id'], ))

    verbose("Optimizing database...", 2)
    conn.commit()
    SQL = "VACUUM"
    execute_sql(conn, SQL)

    return True


def initialize_db(db_file):
    createMode = not(os.path.isfile(db_file))

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

    SQL = "PRAGMA foreign_keys = ON"
    execute_sql(conn, SQL)

    return conn


def initialize_tmdb(apikey):
    tmdb = TMDb()
    tmdb.api_key = apikey

    tmdb.language = 'de'
    tmdb.debug = True

    movie = Movie()
    search = Search()

    return movie, search


def actor_get_popularity(actor):
    popularity = actor.get('popularity')
    return popularity


def query_cast(movie, tmdbid):
    # query actors
    verbose("Querying movie cast online...", 2)
    results = movie.credits(tmdbid)
    # parse result
    cast = []
    for c in results['cast']:
        actor = {
            "name": c['name'],
            "photo": c['profile_path'],
            "popularity": c['popularity'],
            "tmdb_id": c['id'],
            "profile": fetchPoster(c['profile_path'])
        }
        cast.append(actor)
    # sort by popularity
    cast.sort(key=actor_get_popularity, reverse=True)
    return cast


def query_movie(search, name, year):
    verbose(f'Querying movie online: {name} {year}', 2)
    query = {"language": "de", "query": name, "year": year}
    results = search.movies(query)
    if isinstance(results, list):
        if len(results) == 0:
            return None
        else:
            for m in results:
                if m['title'] == name and int(m['release_date'][0:4]) == year:
                    return m
            # no exact match found
            return results[0]
    else:
        return results


def addFileToDb(db, collection, filename, relpath):
    insertSQL = "INSERT INTO files (collection, filename, relpath, movie_id) VALUES (?, ?, ?, NULL)"
    selectSQL = "SELECT * FROM files WHERE collection=? AND filename = ? AND relpath = ?"
    cur = execute_sql(db, selectSQL, (collection, filename, relpath))
    entry = cur.fetchone()
    if entry is None:
        execute_sql(db, insertSQL, (collection, filename, relpath))


def updateFileMeta(db, filename, attributes):
    selectSQL = "SELECT * FROM files WHERE collection=? AND filename = ?"
    cur = execute_sql(db, selectSQL, (attributes['collection'], filename))
    entry = cur.fetchone()
    if entry is None:
        return False
    else:
        parameters = []
        updateSQL = "UPDATE FILES SET "
        for attr in ('size', 'ctime', 'mtime'):
            if attributes[attr] != entry[attr]:
                updateSQL = updateSQL + attr + " = ?, "
                parameters.append(attributes[attr])
        updateSQL = updateSQL + "lastmod=(cast(strftime('%s','now') as int)) WHERE filename = ? AND collection = ?"
        if len(parameters) > 0:
            parameters.append(filename)
            parameters.append(attributes['collection'])
            result = execute_sql(db, updateSQL, parameters)
            return result
        else:
            return False


def addMovieToDb(db, movie):
    insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, year, description, popularity, score, poster) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    result = execute_sql(db, insertSQL, (movie['tmdb_id'], movie['title'], movie['orig_title'], movie['release_year'], movie['description'], movie['popularity'], movie['score'], movie['poster']))
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


def scanDir(db, collection, rootDir, recursiveSearch=False):
    " scan all files found "
    idx = 0
    verbose("Scanning for new files...", 2)

    scanPath = os.path.join(rootDir, '')
    if recursiveSearch:
        scanPath = scanPath + '**/'
    fn = scanPath + '* ([0-9][0-9][0-9][0-9])*.'
    movies = glob.glob(fn + 'mp4', recursive=recursiveSearch)
    for ext in ('avi', 'm4v', 'mkv', 'mov', 'mp4', 'mpg'):
        movies.extend(glob.glob(fn + ext, recursive=recursiveSearch))

    for m in movies:
        idx = idx + 1
        f = os.path.basename(m)
        absPath = os.path.dirname(m)
        relPath = os.path.relpath(absPath, rootDir)
        size = os.path.getsize(m)
        ctime = os.path.getctime(m)
        mtime = os.path.getmtime(m)
        addFileToDb(db, collection, f, relPath)
        updateFileMeta(db, f, {"collection": collection, "size": size, "ctime": ctime, "mtime": mtime})
    verbose(f"{idx} files found")

    " check if all database files exist "
    verbose("Scanning for obsolete files...", 2)
    selectSQL = "SELECT id, filename, relpath FROM files"
    if collection:
        selectSQL = selectSQL + f" WHERE collection='{collection}'"
    selectSQL = selectSQL + " ORDER BY relpath ASC, filename ASC"
    cur = execute_sql(db, selectSQL, ())
    for row in cur.fetchall():
        fn = rootDir + '/'
        if row['relpath']:
            fn = fn + row['relpath'] + '/'
        fn = fn + row['filename']

        if (not os.path.isfile(fn)):
            deleteSQL = f"DELETE FROM files WHERE id = {row['id']}"
            execute_sql(db, deleteSQL)

    " finish "
    db.commit()
    return None


def fetchPoster(posterPath):
    # https://image.tmdb.org/t/p/w200/zWRlFDY03muF921z39Xg7Py5WRK.jpg
    baseurl = 'https://image.tmdb.org/t/p/w154'
    if posterPath:
        url = baseurl + posterPath
        poster = urlopen(url).read()
        return poster
    else:
        return None


def lookupMovie(db, title, year):
    verbose("Lookup movie: " + title, 2)
    cur = db.cursor()
    selectSQL = "SELECT id FROM movies WHERE title=? AND year=?"
    cur = execute_sql(db, selectSQL, (title, year))
    entry = cur.fetchone()
    if entry is None:
        result = query_movie(search, title, year)
        if result is not None:
            movie = {
                "tmdb_id": result['id'],
                "title": result['title'],
                "orig_title": result['original_title'],
                "release_year": result['release_date'][0:4],
                "description": result['overview'] if result['overview'] else None,
                "popularity": result['popularity'],  # https://developers.themoviedb.org/3/getting-started/popularity
                "score": result['vote_average'] * 10,
                "poster": fetchPoster(result['poster_path'])
            }
            return addMovieToDb(db, movie)
        else:
            verbose("Cannot find online: " + title, 1)
            if not UNKNOWN_IGNORE:
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


def assignMovieToFile(db, fid, mid):
    cur = db.cursor()
    updateSQL = "UPDATE files SET movie_id = ? WHERE id = ?"
    cur.execute(updateSQL, (mid, fid))
    return True


def scanMovies(db, search):
    selectSQL = "SELECT id, filename FROM files WHERE (movie_id IS NULL or movie_id=0) ORDER BY filename ASC"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        m = re.search('(.*) \(([0-9][0-9][0-9][0-9])\).+', row['filename'])
        basename = m.group(1)
        year = int(m.group(2))
        m_id = lookupMovie(db, basename, year)
        assignMovieToFile(db, row['id'], m_id)
        db.commit()
    return None


def scanActors(db, movie):
    verbose("Scanning for actors...", 2)
    selectSQL = "SELECT id, title, tmdb_id FROM movies WHERE tmdb_id IS NOT NULL AND NOT (id IN (SELECT DISTINCT m_id FROM actors_movies))"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        verbose("Lookup cast for " + row['title'], 2)
        cast = query_cast(movie, row['tmdb_id'])
        for actor in cast:
            aid = addActorToDb(db, actor)
            addActorToMovieDb(db, row['id'], aid)
        db.commit()
    return None


if __name__ == '__main__':

    clihelp = sys.argv[0] + ' [-q] [-r] [-v] -d <dbfile> -c <collection> -p <path> -t <type> -k <apikey> [-a]'

    tmdbApiKey = None
    dbfile = None
    libPath = None
    libType = None
    collection = None
    recursiveSearch = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hqvd:p:t:k:c:ar", ["db=", "path=", "type=", 'key=', 'add-unknown=', "collection="])
    except getopt.GetoptError:
        verbose(clihelp, 0)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(clihelp)
            sys.exit()
        elif opt == '-q':
            VERBOSITY_LEVEL = 0
        elif opt == '-r':
            recursiveSearch = True
        elif opt == '-v':
            VERBOSITY_LEVEL = VERBOSITY_LEVEL + 1
        elif opt in ("-d", "--db"):
            dbfile = arg
        elif opt in ("-p", "--path"):
            libPath = arg
        elif opt in ("-t", "--type"):
            libType = arg
        elif opt in ("-k", "--key"):
            tmdbApiKey = arg
        elif opt in ("-c", "--collection"):
            collection = arg
        elif opt in ("-a", "--add-unknown"):
            UNKNOWN_IGNORE = False

    if tmdbApiKey is None or dbfile is None or libPath is None or libType is None or libType != "movies" or collection is None:
        print("Usage: " + clihelp)
        sys.exit(2)

    verbose("Verbosity level: " + str(VERBOSITY_LEVEL), 2)
    db = initialize_db(dbfile)
    movie, search = initialize_tmdb(tmdbApiKey)
    scanDir(db, collection, libPath, recursiveSearch)
    scanMovies(db, search)
    scanActors(db, movie)
    cleanup_db(db)
