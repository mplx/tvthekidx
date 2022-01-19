#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sqlite3
import glob
import urllib.parse
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


def verbose(text, level = 1):
    global VERBOSITY_LEVEL

    if VERBOSITY_LEVEL >= level:
        print(text)


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
    except Error as e:
        print(e)
    else:
        return conn


def execute_sql(conn, sql, param = None):
    if param is None: 
        param = []

    try:
        c = conn.cursor()
        c.execute(sql, param)
        conn.commit()
        return c
    except Error as e:
        print(e)


def cleanup_db(conn):
    SQL = "DELETE FROM movies WHERE tmdb_id in (SELECT tmdb_id FROM movies GROUP BY tmdb_id HAVING COUNT(*)>1)"
    result = execute_sql(conn, SQL)
    SQL = "DELETE FROM files WHERE movie_id NOT IN (SELECT id FROM movies)"
    result = execute_sql(conn, SQL)
    SQL = "VACUUM"
    result = execute_sql(conn, SQL)
    return True


def initialize_db(db_file):
    createMode = not(os.path.isfile(db_file))
    if createMode:
        verbose("Creating database...", 2)
        conn = create_connection(db_file)
        SQL = 'CREATE TABLE "files" ("id" INTEGER, "filename" TEXT NOT NULL UNIQUE, "movie_id" INTEGER DEFAULT NULL, "title" TEXT, "year" INTEGER, PRIMARY KEY("id" AUTOINCREMENT))'
        result = execute_sql(conn, SQL)
        SQL = 'CREATE TABLE "movies" ("id" INTEGER NOT NULL, "title" TEXT NOT NULL, "title_orig" TEXT NOT NULL, "year" INTEGER NOT NULL, "description" TEXT, "popularity" REAL DEFAULT 0, "score" REAL DEFAULT 0, "poster" BLOB, "tmdb_id" INTEGER, PRIMARY KEY("id" AUTOINCREMENT) )'
        result = execute_sql(conn, SQL)
    else:
        verbose("Connecting database...", 2)
        conn = create_connection(db_file)

    return conn


def initialize_tmdb(apikey):
    tmdb = TMDb()
    tmdb.api_key = apikey

    tmdb.language = 'de'
    tmdb.debug = True

    movie = Movie()
    search = Search()

    return movie, search


def query_movie(search, name, year):
    #results = query_movie(search, 'Die fabelhafte Welt der Amélie', 2001)
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
            #no exact match found
            return results[0]
    else:
        return results


def addFileToDb(db, filename, title, year, extension):
    selectSQL = "SELECT * FROM files WHERE filename = ?"
    insertSQL = "INSERT INTO files (filename, title, year) VALUES (?, ?, ?)"

    cur = execute_sql(db, selectSQL, (filename, ))
    entry = cur.fetchone()

    if entry is None:
        result = execute_sql(db, insertSQL, (filename, title, year))
        db.commit()


def addMovieToDb(db, movie):
    insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, year, description, popularity, score, poster) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    result =  execute_sql(db, insertSQL, (movie['tmdb_id'], movie['title'], movie['orig_title'], movie['release_year'], movie['description'], movie['popularity'], movie['score'], movie['poster']))
    return result.lastrowid


def scanDir(db, scanPath):
    " scan all files found "
    idx = 0
    verbose("Scanning for new files...", 2)
    fn = scanPath + '/* ([0-9][0-9][0-9][0-9]).mp4'
    movies = glob.glob(fn)
    for m in movies:
        idx = idx + 1
        f = os.path.basename(m)
        m = re.search('(.*) \(([0-9][0-9][0-9][0-9])\)\.(mp4)', f)
        basename = m.group(1)
        year = m.group(2)
        ext = m.group(3)
        result = addFileToDb(db, f, basename, year, ext)
    verbose(f"{idx} files found")

    " check if all database files exist "
    verbose("Scanning for obsolete files...", 2)
    selectSQL = "SELECT id, filename FROM files ORDER BY filename ASC"
    cur = execute_sql(db, selectSQL, ())
    for row in cur.fetchall():
        fn = scanPath + '/' + row['filename']
        if (not os.path.isfile(fn)):
            deleteSQL = f"DELETE FROM files WHERE id = {row['id']}"
            result = execute_sql(db, deleteSQL)

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
    verbose("Lookup... " + title, 2)
    cur = db.cursor()
    selectSQL = f"SELECT id FROM movies WHERE title=? AND year=?"
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
                    "popularity": result['popularity'], # https://developers.themoviedb.org/3/getting-started/popularity
                    "score": result['vote_average'] * 10,
                    "poster": fetchPoster(result['poster_path']),
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
    result = cur.execute(updateSQL, (mid, fid))
    db.commit()
    return True


def scanMovies(db, search):
    selectSQL = "SELECT id, title, year FROM files WHERE movie_id IS NULL ORDER BY filename ASC"
    cur = execute_sql(db, selectSQL)
    for row in cur.fetchall():
        m_id = lookupMovie(db, row['title'], row['year'])
        result = assignMovieToFile(db, row['id'], m_id)


if __name__ == '__main__':

    clihelp = sys.argv[0] + ' -v -d <dbfile> -p <path> -t <type> -k <apikey>'
    tmdbApiKey = None
    dbfile = None
    libPath = None
    libType = None

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hqvd:p:t:k:a", ["db=","path=","type=",'key=', 'add-unknown='])
    except getopt.GetoptError:
        verbose(clihelp, 0)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(clihelp)
            sys.exit()
        elif opt == '-q':
            VERBOSITY_LEVEL = 0
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
        elif opt in ("-a", "--add-unknown"):
            UNKNOWN_IGNORE = False

    if tmdbApiKey is None or dbfile is None or libPath is None or libType is None or libType != "movies":
        print("Usage: " + clihelp)
        sys.exit(2)

    verbose("Verbosity level: " + str(VERBOSITY_LEVEL), 2)
    db = initialize_db(dbfile)
    movie, search = initialize_tmdb(tmdbApiKey)
    scanDir(db, libPath)
    scanMovies(db, search)
    result = cleanup_db(db)
