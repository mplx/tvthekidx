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

verboseSetting = False

def verbose(text):
    global verboseSetting

    if verboseSetting:
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


def execute_sql(conn, sql):
    #print(sql)
    try:
        c = conn.cursor()
        c.execute(sql)
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
    conn = create_connection(db_file)
    #create_table(conn, "SQL")
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
    verbose(f'Querying movie online: {name} {year}')
    query = {"language": "de", "query": name, "year": year}
    results = search.movies(query)
    if isinstance(results, list):
        if len(results) == 0:
            return None
        else:
            return results[0]
    else:
        return results


def addFileToDb(db, filename, title, year, extension):
    selectSQL = "SELECT * FROM files WHERE filename = ?"
    insertSQL = f"INSERT INTO files (filename, title, year) VALUES ('{filename}', '{title}', {year})"
    cur = db.cursor()
    result = cur.execute(selectSQL, (filename,))
    entry = cur.fetchone()

    if entry is None:
        execute_sql(db, insertSQL)
        db.commit()


def scanDir(db, scanPath):
    " scan all files found "
    idx = 0
    verbose("Scanning for new files...")
    fn = scanPath + '/* ([0-9][0-9][0-9][0-9]).mp4'
    verbose("Pattern: " + fn)
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
    verbose("Scanning for obsolete files...")
    selectSQL = "SELECT id, filename FROM files ORDER BY filename ASC"
    cur = execute_sql(db, selectSQL)
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
    verbose("Lookup... " + title)
    cur = db.cursor()
    selectSQL = f"SELECT id FROM movies WHERE title='{title}' AND year={year}"
    #verbose(selectSQL)
    cur.execute(selectSQL)
    entry = cur.fetchone()
    if entry is None:
        result = query_movie(search, title, year)
        if result is not None:
            tmdb_id = result['id']
            title = result['title']
            orig_title = result['original_title']
            release_year = result['release_date'][0:4]
            description = result['overview']
            popularity = result['popularity'] # https://developers.themoviedb.org/3/getting-started/popularity
            score = result['vote_average'] * 10
            poster = fetchPoster(result['poster_path'])
            insertSQL = "INSERT INTO movies(tmdb_id, title, title_orig, year, description, popularity, score, poster) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            result = cur.execute(insertSQL, (tmdb_id, title, orig_title, release_year, description, popularity, score, poster))
            db.commit()
            return cur.lastrowid
        else:
            print("Cannot find online:" + title)
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
        opts, args = getopt.getopt(sys.argv[1:], "hvd:p:t:k:", ["db=","path=","type=",'key='])
    except getopt.GetoptError:
        print(clihelp)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(clihelp)
            sys.exit()
        elif opt == '-v':
            verboseSetting = True
        elif opt in ("-d", "--db"):
            dbfile = arg
        elif opt in ("-p", "--path"):
            libPath = arg
        elif opt in ("-t", "--type"):
            libType = arg
        elif opt in ("-k", "--key"):
            tmdbApiKey = arg

    if tmdbApiKey is None or dbfile is None or libPath is None or libType is None or libType != "movies":
        print("Usage: " + clihelp)
        sys.exit(2)

    db = initialize_db(dbfile)
    movie, search = initialize_tmdb(tmdbApiKey)
    scanDir(db, libPath)
    scanMovies(db, search)
    result = cleanup_db(db)
