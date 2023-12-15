#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2023 developer@mplx.eu

import sqlite3
import base64
import datetime
import glob
import os
import re
import sys
import argparse

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

    if DBVERSION == 1:
        verbose("Database up-to-date", 1)


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
    for ext in ('avi', 'm4v', 'mkv', 'mov', 'mpg'):
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


def lookupMovie(db, search, title, year):
    global UNKNOWN_IGNORE

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
        m = re.search(r'(.*) \(([0-9][0-9][0-9][0-9])\).+', row['filename'])
        basename = m.group(1)
        year = int(m.group(2))
        m_id = lookupMovie(db, search, basename, year)
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


def getActors(db, where=None, orderby="popularity DESC, name ASC"):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT a.* FROM actors a"
    if where:
        selectSQL = f"{selectSQL} JOIN actors_movies am ON am.a_id=a.id JOIN movies m ON am.m_id=m.id JOIN files f ON f.movie_id = m.id WHERE {where}"
    if orderby:
        selectSQL = f"{selectSQL} ORDER BY {orderby}"
    cur.execute(selectSQL)
    return cur.fetchall()


def getCast(db, mid, limit=None):
    cur = db.cursor()
    selectSQL = "SELECT a.* FROM actors_movies c JOIN actors a ON c.a_id = a.id JOIN movies m ON c.m_id = m.id WHERE m.id = ? ORDER BY a.popularity DESC"
    if limit:
        selectSQL = f"{selectSQL} LIMIT {limit}"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getCollections(db, mid):
    cur = db.cursor()
    selectSQL = "SELECT DISTINCT id, collection, filename, size, added, ctime FROM files WHERE movie_id = ? ORDER BY collection ASC"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getMoviesByActor(db, aid):
    cur = db.cursor()
    selectSQL = "SELECT m.id, m.title, m.score, m.year FROM actors_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ? ORDER BY m.title COLLATE NOCASE ASC, m.year ASC"
    cur.execute(selectSQL, (aid, ))
    return cur.fetchall()


def writeHeader(f, title="TVThek Index"):
    now = datetime.datetime.now()
    f.write('<!DOCTYPE html>\n')
    f.write('<html lang="de">\n')
    f.write('<head>\n')
    f.write('   <meta charset="utf-8"/>\n')
    f.write('   <meta name="viewport" content="width=device-width, initial-scale=1.0">\n')
    f.write('   <title>' + title + ' - ' + now.strftime("%d.%m.%Y") + '</title>\n')
    f.write('   <link type="text/css" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">\n')
    f.write('   <style>\n')
    f.write('       .row-striped:nth-child(odd) { background-color: #eafafa; }\n')
    f.write('       .row-striped:nth-child(even) { background-color: #ffffff; }\n')
    f.write('       h1,h2,h3,h4 { padding-top: 54px; margin-top: -54px; }\n')
    f.write('       body { padding-top: 54px; }\n')
    f.write('   </style\n')
    f.write('</head>\n')
    f.write('<body>\n')
    f.write('<nav class="navbar navbar-expand-lg fixed-top navbar-light bg-light">')
    f.write('   <div class="container-fluid">')
    f.write('       <a class="navbar-brand" href="#">' + title + '</a>')
    f.write('       <div class="collapse navbar-collapse" id="navbarSupportedContent">')
    f.write('           <ul class="navbar-nav me-auto mb-2 mb-lg-0">')
    f.write('               <li class="nav-item"><a class="nav-link" href="#top">Top</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#new">Neu</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#index">Verzeichnis</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#actor">Darsteller</a></li>')
    f.write('           </ul>')
    f.write('           <form class="d-flex" role="search" onsubmit="return false;">')
    f.write('               <div id="spinner" class="spinner-grow text-secondary" role="status"><span class="visually-hidden"></span></div>')
    f.write('               <input id="searchInput" class="form-control me-1" type="search" placeholder="Titel" aria-label="Titel">')
    f.write('           </form>')
    f.write('           <span class="navbar-text">Stand: ' + now.strftime("%d.%m.%Y") + '</span>')
    f.write('       </div>')
    f.write('   </div>')
    f.write('</nav>\n')
    f.write('<div class="container">\n')


def writeFooter(f):
    f.write('</div>\n')
    f.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>\n')
    f.write('''<script>
        var TVAPP = {};

        function handleSearch() {
            const searchTerm = searchInput.value.trim().toLowerCase();

            document.getElementById("spinner").style.visibility = 'visible';

            if (searchTerm.length === 0) {
                document.getElementById("top").removeAttribute("hidden");
                document.getElementById("top1").removeAttribute("hidden");
                document.getElementById("top2").removeAttribute("hidden");
                document.getElementById("new").removeAttribute("hidden");
                document.getElementById("new1").removeAttribute("hidden");
                document.getElementById("actor").removeAttribute("hidden");
                document.getElementById("actors").removeAttribute("hidden");
            } else {
                document.getElementById("top").setAttribute("hidden", "hidden");
                document.getElementById("top1").setAttribute("hidden", "hidden");
                document.getElementById("top2").setAttribute("hidden", "hidden");
                document.getElementById("new").setAttribute("hidden", "hidden");
                document.getElementById("new1").setAttribute("hidden", "hidden");
                document.getElementById("actor").setAttribute("hidden", "hidden");
                document.getElementById("actors").setAttribute("hidden", "hidden");
            }

            TVAPP.cntFound = 0;
            TVAPP.cntNotFound = 0;

            rows.forEach(row => {
                const dataSearch = row.getAttribute('data-search').toLowerCase();
                if (searchTerm.length === 0) {
                    row.style.display = 'flex';
                    TVAPP.cntFound++;
                } else {
                    if (dataSearch.includes(searchTerm)) {
                        row.style.display = 'flex';
                        TVAPP.cntFound++;
                    } else {
                        row.style.display = 'none';
                        TVAPP.cntNotFound++;
                    }
                }
            });

            if (TVAPP.cntFound == 0) {
                document.getElementById("moviecounter").innerHTML = 'keine Filme gefunden';
            } else if (TVAPP.cntNotFound == 0) {
                document.getElementById("moviecounter").innerHTML = TVAPP.cntFound + ' Filme gelistet';
            } else {
                document.getElementById("moviecounter").innerHTML = TVAPP.cntFound + ' / ' + (TVAPP.cntFound+TVAPP.cntNotFound) + ' Filme gefunden';
            }

            document.getElementById("spinner").style.visibility = 'hidden';
        }

        const searchInput = document.getElementById('searchInput');
        const rows = document.querySelectorAll('#movies .row');

        searchInput.addEventListener('input', handleSearch);
        searchInput.addEventListener('focus', function() { this.select(); });

        window.addEventListener("keydown", (e) => {
          if (e.code === 'F3' || ((e.ctrlKey || e.metaKey) && e.code === 'KeyF')) {
            e.preventDefault();
            searchInput.focus();
          }
        })

        document.getElementById("spinner").style.visibility = 'hidden';

        window.addEventListener("keydown", (e) => {
          if (e.code === 'F3' || ((e.ctrlKey || e.metaKey) && e.code === 'KeyF')) {
            e.preventDefault();
            const search = document.querySelector('#searchInput')
            search.focus()
          }
        })
    </script>\n''')
    f.write('</body>\n')
    f.write('</html>\n')


def writeMoviesImageTitle(db, f, collection):
    f.write('<h3 id="top">Top</h3>')

    orderBy = "score DESC, year DESC, m.title COLLATE NOCASE ASC"
    whereSql = "NOT (poster IS NULL)"
    if collection:
        whereSql = whereSql + " AND ("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    movies = getMovies(db, whereSql, orderBy, "0,24")
    f.write('<section id="top1">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
        else:
            poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
        posterhtml = f"<a href=\"#movie-{id}\"><img width=\"105\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
        f.write(f'{posterhtml}')
    f.write('\n</section>\n')

    movies = getMovies(db, whereSql, orderBy, "24,84")
    f.write('<section id="top2">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
        else:
            poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
        posterhtml = f"<a href=\"#movie-{id}\"><img width=\"60\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
        f.write(f'{posterhtml}')
    f.write('\n</section>\n')

    f.write('<h3 id="new">Neu</h3>')

    orderBy = "added DESC, score DESC, year DESC, m.title COLLATE NOCASE ASC"
    movies = getMovies(db, whereSql, orderBy, "0,84")
    f.write('<section id="new1">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
        else:
            poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
        posterhtml = f"<a href=\"#movie-{id}\"><img width=\"60\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
        f.write(f'{posterhtml}')
    f.write('\n</section>\n')


def movieRatingColor(score):
    scorecolor = "info"
    if score == 0:
        scorecolor = 'warning'
    elif score < 50:
        scorecolor = 'danger'
    elif score >= 70:
        scorecolor = 'success'
    return scorecolor


def writeMoviesDetail(db, f, collection):
    f.write('<h3 id="index">Verzeichnis</h3>')

    whereSql = ""
    fileDetail = 0
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
            fileDetail += 1
        whereSql = whereSql[0:-4] + ")"

    movies = getMovies(db, whereSql, "m.title COLLATE NOCASE ASC, year ASC", None)
    f.write('<section id="movies">')
    for m in movies:
        id = m['id']
        title = m['title']
        title_orig = m['title_orig']
        description = m['description'] if m['description'] else ""
        if len(description) > 800:
            description = description[0:800] + "[...]"
        year = m['year']
        tmdbid = m['tmdb_id']
        score = int(m['score'])
        scorecolor = movieRatingColor(score)
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
            posterhtml = f"<a href=\"https://www.themoviedb.org/movie/{tmdbid}\"><img title=\"{title}\" src=\"data:image/png;base64,{poster}\" /></a>"
        else:
            posterhtml = "&nbsp;"
        titleext = ""
        if m["title_orig"] != m['title']:
            titleext = f" <span class='origtitle'>{title_orig}</span>"
        actors = ""
        cast = getCast(db, id, "0,15")
        for actor in cast:
            actors = actors + '<a href="#actor-' + str(actor['id']) + '" title="' + str(int(actor['popularity'])) + ' Pkt." style="text-decoration:none" class="badge bg-info">' + actor['name'] + '</a> '
        metadatastr = ""
        collectionstr = ""
        collections = getCollections(db, id)
        for col in collections:
            if col['collection'] is not None:
                colstr = col['collection']
            else:
                colstr = "k.A."
            colsize = "{:.2f}".format(col['size'] / 1024 / 1024 / 1024) + ' GB'
            dbtime = datetime.datetime.fromtimestamp(col['added']).strftime('%d.%m.%Y')
            fctime = datetime.datetime.fromtimestamp(col['ctime']).strftime('%d.%m.%Y')
            tmdbid = m["tmdb_id"]
            movieid = m["id"]
            fileid = col["id"]
            if fileDetail != 1:
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary\" style=\"text-decoration:none\" title=\"{col['filename']} [{colsize}]\" href=\"{col['filename']}\">{colstr}</a> "
            else:
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary\" style=\"text-decoration:none\" title=\"{col['filename']}\" href=\"{col['filename']}\">{colstr}</a> "
                metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Größe\">{colsize}</span> "
                if col['ctime'] > col['added']:
                    metadatastr = metadatastr + f"<span class=\"badge bg-info\" title=\"Datei (Datenbank {dbtime})\">{fctime}</span> "
                else:
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Datei\">{fctime}</span> "
                if m["tmdb_id"] is not None:
                    metadatastr = metadatastr + f"<a class=\"badge bg-secondary\" style=\"text-decoration:none\" title=\"TheMovieDatabase={tmdbid} DbMovieID={movieid} DbFileID={fileid}\" href=\"https://www.themoviedb.org/movie/{tmdbid}\">TMDB</a> "
                else:
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"DbMovieID={movieid} DbFileID={fileid}\">ID</span> "
            metadatastr = metadatastr + "<br />"
        copyselector = ''  # '<div class="form-check form-switch"><input class="form-check-input" type="checkbox" id="flexSwitchCheckDefault"></div>'
        if fileDetail == 1:
            collectionstr = f"<dt>Bibliothek</dt><dd>{collectionstr}</dd>"
            metadatastr = f"<dt>Details</dt><dd>{metadatastr}</dd>"
        else:
            collectionstr = f"<dt>Bibliotheken</dt><dd>{collectionstr}</dd>"
            metadatastr = ""
        f.write(f"""
                <div class="row row-striped p-3" data-search='["{title}"]'>
                    <div class="col" style="hyphens: auto;"><h3 id="movie-{id}">{title}</h3>{titleext}{copyselector}</div>
                    <div class="col">{posterhtml}</div>
                    <div class="col">
                        <dl>
                            <dt>Jahr</dt><dd><span class="badge bg-secondary">{year}</span></dd>
                            <dt>Wertung</dt><dd><span class="badge bg-{scorecolor}">{score}</span></dd>
                            {collectionstr}{metadatastr}
                        </dl>
                    </div>
                    <div class="col-6"><div class="description"><p style="hyphens: auto; text-align: justify;">{description}</p><p>{actors}</p></div></div>
            </div>""")
    cntmovies = len(movies)
    if cntmovies == 1:
        f.write(f"<span id='moviecounter'>{cntmovies} Film gelistet</span>")
    else:
        f.write(f"<span id='moviecounter'>{cntmovies} Filme gelistet</span>")
    f.write('\n</section>\n')


def actorListedChoice(mcnt=0, popularity=0):
    if popularity >= 40:
        return True
    elif mcnt > 3:
        return True
    elif popularity >= 10 and mcnt > 1:
        return True
    elif popularity >= 5 and mcnt > 2:
        return True
    return False


def writeActorsDetail(db, f, collection):
    whereSql = ""
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    actors = getActors(db, whereSql)

    f.write('<h3 id="actor">Darsteller</h3>')
    f.write('<section id="actors">')
    i = 0
    total = len(actors)
    for a in actors:
        id = a['id']
        name = a['name']
        popularity = int(a['popularity'])
        tmdbid = a['tmdb_id']
        if popularity > 20:
            popcolor = 'success'
        else:
            popcolor = 'secondary'
        popularityhtml = f'<dl><dt>Popularität</dt><dd><span class="badge bg-{popcolor}">{popularity}</span></dd></dl>'
        if popularity == 0:
            popularityhtml = "&nbsp;"
        if a['profile']:
            profile = base64.b64encode(a['profile']).decode('ascii')
            profilehtml = f"<a href=\"https://www.themoviedb.org/person/{tmdbid}\"><img width=\"25%\" title=\"{name}\" src=\"data:image/png;base64,{profile}\" /></a>"
        else:
            profilehtml = "&nbsp;"
        movies = getMoviesByActor(db, id)
        if actorListedChoice(len(movies), popularity):
            i = i + 1
            f.write(f"""
                    <div class="row row-striped p-3" data-search='["{name}"]'>
                        <div class="col"><h4 id="actor-{id}">{name}</h4></div>
                        <div class="col">{profilehtml}</div>
                        <div class="col">{popularityhtml}</div>
                        <div class="col-6"><div class="description">""")
            for m in movies:
                mid = m['id']
                title = m['title']
                year = m['year']
                score = int(m['score'])
                scorecolor = movieRatingColor(m['score'])
                f.write(f'<a href="#movie-{mid}" style="text-decoration:none" title="{year} / {score}%" class="badge bg-{scorecolor}">{title}</a> ')
            f.write("</div></div></div>")
    f.write(f"{i}/{total} Schauspieler gelisted")
    f.write('\n</section>\n')


def indexer(args):
    global UNKNOWN_IGNORE

    if args.addUnknown:
        UNKNOWN_IGNORE = False

    if args.libType != "movies":
        print("ERROR: currently only type movies supported")
        sys.exit(2)

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = initialize_db(args.dbfile)
    movie, search = initialize_tmdb(args.tmdbApiKey)

    scanDir(db, args.collection, args.libPath, args.recursiveSearch)
    scanMovies(db, search)
    scanActors(db, movie)


def exporter(args):
    collection = None
    if args.collectionStr:
        collection = args.collectionStr.split(",")

    if not os.path.isfile(args.dbfile):
        print(f"ERROR: database '{args.dbfile}' not found")
        sys.exit(2)

    db = create_connection(args.dbfile)
    with open(args.outputFile, 'w', encoding='utf8') as f:
        writeHeader(f, args.title)
        if not args.skipHeader:
            writeMoviesImageTitle(db, f, collection)
        writeMoviesDetail(db, f, collection)
        if not args.skipActors:
            writeActorsDetail(db, f, collection)
        writeFooter(f)


def dbtools(args):
    match args.action:
        case 'create':
            if os.path.isfile(args.dbfile):
                print(f"ERROR: database '{args.dbfile}' already exists")
                sys.exit(2)
            initialize_db(args.dbfile)
        case 'compress':
            if not os.path.isfile(args.dbfile):
                print(f"ERROR: database '{args.dbfile}' not found")
                sys.exit(2)
            db = create_connection(args.dbfile)
            cleanup_db(db)
        case 'upgrade':
            if not os.path.isfile(args.dbfile):
                print(f"ERROR: database '{args.dbfile}' not found")
                sys.exit(2)
            upgrade_db(args.dbfile)
        case _:
            print("ERROR: no or unknown action specified")
            sys.exit(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='tvthekidx', description='tvthek index')
    parser.add_argument('--quiet', '-q', action='store_true', dest='quiet', help='quiet (set verbose to 0)')
    parser.add_argument('--verbose', '-v', action='count', dest='verbose', default=0, help='verbosity level')

    subparsers = parser.add_subparsers()
    subparsers.required = True

    indexerparser = subparsers.add_parser('index', help='create and maintain the tvthekidx database')
    indexerparser.set_defaults(func=indexer)
    indexerparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    indexerparser.add_argument('--path', '-p', action='store', dest='libPath', help='path to scan', required=True)
    indexerparser.add_argument('--type', '-t', action='store', dest='libType', default='movies', help='type of content')
    indexerparser.add_argument('--key', '-k', action='store', dest='tmdbApiKey', help='TMDB API key', required=True)
    indexerparser.add_argument('--collection', '-c', action='store', dest='collection', default='TVthek', help='collection name')
    indexerparser.add_argument('--recursive', '-r', action='store_true', dest='recursiveSearch', help='recursive search')
    indexerparser.add_argument('--add-unknown', '-a', action='store_true', dest='addUnknown', help='add unknown content to database')

    exporterparser = subparsers.add_parser('export', help='export tvthekidx content')
    exporterparser.set_defaults(func=exporter)
    exporterparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    exporterparser.add_argument('--title', '-t', action='store', dest='title', default='TVThek Index', help='page title')
    exporterparser.add_argument('--output', '-o', action='store', dest='outputFile', default='tvthek.html', help='oputput file')
    exporterparser.add_argument('--collection', '-c', action='store', dest='collectionStr', default=None, help='comma-separated list of collections')
    exporterparser.add_argument('--skip-actors', action='store_true', dest='skipActors', help='do not include actors section')
    exporterparser.add_argument('--skip-header', action='store_true', dest='skipHeader', help='do not include header with top and new sections')

    exporterparser = subparsers.add_parser('database', help='database tools')
    exporterparser.set_defaults(func=dbtools)
    exporterparser.add_argument('--database', '-d', action='store', dest='dbfile', default='tvthek.db', help='TVthekIdx database')
    exporterparser.add_argument('--action', '-a', action='store', dest='action', default=None, help='create/compress/upgrade')

    args = parser.parse_args()

    if args.quiet:
        VERBOSITY_LEVEL = 0
    else:
        VERBOSITY_LEVEL = args.verbose + 1
        verbose("Verbosity level: " + str(VERBOSITY_LEVEL), 2)

    args.func(args)
