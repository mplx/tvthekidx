#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import base64
import datetime
import sys
import getopt
import os


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
    except BaseException as e:
        print(e)
    else:
        return conn


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
    selectSQL = "SELECT DISTINCT collection, filename FROM files WHERE movie_id = ? ORDER BY collection ASC"
    cur.execute(selectSQL, (mid, ))
    return cur.fetchall()


def getMoviesByActor(db, aid):
    cur = db.cursor()
    selectSQL = "SELECT m.id, m.title, m.score, m.year FROM actors_movies c JOIN movies m ON c.m_id = m.id WHERE c.a_id = ? ORDER BY m.year ASC, m.title ASC"
    cur.execute(selectSQL, (aid, ))
    return cur.fetchall()


def writeHeader(f, title="TVThek Index"):
    now = datetime.datetime.now()
    f.write('<!DOCTYPE html>')
    f.write('<html lang="de">')
    f.write('<header>')
    f.write('<meta charset="utf-8"/>\n')
    f.write('<title>' + title + ' - ' + now.strftime("%d.%m.%Y") + '</title>\n')
    f.write('<link type="text/css" href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">\n')
    f.write('<style>\n')
    f.write('.row-striped:nth-child(odd) { background-color: #eafafa; }\n')
    f.write('.row-striped:nth-child(even) { background-color: #ffffff; }\n')
    f.write('</style\n')
    f.write('</header>\n')
    f.write('</body>\n')
    f.write('<div class="container">')
    f.write('<h1>' + title + '</h1>\nStand: ' + now.strftime("%d.%m.%Y"))


def writeFooter(f):
    f.write('</div>')
    f.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>')
    f.write('</body>')
    f.write('</html>')


def writeMoviesImageTitle(db, f, collection):
    orderBy = "score DESC, year DESC, m.title COLLATE NOCASE ASC"
    whereSql = "NOT (poster IS NULL)"
    if collection:
        whereSql = whereSql + " AND ("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    movies = getMovies(db, whereSql, orderBy, "0,24")
    f.write('<section id="img1">\n')
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

    movies = getMovies(db, whereSql, orderBy, "24,126")
    f.write('<section id="img2">\n')
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
    whereSql = ""
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
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
        collectionstr = ""
        collections = getCollections(db, id)
        for col in collections:
            if col['collection'] is None:
                colstr = "k.A."
            else:
                colstr = col['collection']
            collectionstr = collectionstr + f"<a class=\"badge bg-secondary\" style=\"text-decoration:none\" title=\"{col['filename']}\" href=\"{col['filename']}\">{colstr}</a> "
        f.write(f"""
                <div class="row row-striped p-3" id="movie-{id}" data-search='["{title}"]'>
                    <div class="col" style="hyphens: auto;"><h3>{title}</h3>{titleext}</div>
                    <div class="col">{posterhtml}</div>
                    <div class="col">
                        <dl>
                            <dt>Jahr</dt><dd><span class="badge bg-secondary">{year}</span></dd>
                            <dt>Wertung</dt><dd><span class="badge bg-{scorecolor}">{score}</span></dd>
                            <dt>Kollektionen</dt><dd>{collectionstr}</dd>
                        </dl>
                    </div>
                    <div class="col-6"><div class="description"><p style="hyphens: auto; text-align: justify;">{description}</p><p>{actors}</p></div></div>
            </div>""")
    cntmovies = len(movies)
    if cntmovies == 1:
        f.write(f"{cntmovies} Film gelistet")
    else:
        f.write(f"{cntmovies} Filme gelistet")
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

    f.write("<h3>Darsteller</h3>")
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
                    <div class="row row-striped p-3" id="actor-{id}" data-search='["{name}"]'>
                        <div class="col"><b>{name}</b></div>
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


if __name__ == '__main__':

    clihelp = sys.argv[0] + ' [-v] [-t <title>] -d <dbfile> [-c <collection>] -o <outputfile>'

    databaseFile = None
    outputFile = None
    collection = None
    title = "TVThek Index"

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvt:d:o:c:", ["db=", "ofile=", "collection="])
    except getopt.GetoptError:
        print(clihelp)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print(clihelp)
            sys.exit()
        elif opt == '-v':
            verboseSetting = True
        elif opt == '-t':
            title = arg
        elif opt in ("-d", "--db"):
            databaseFile = arg
        elif opt in ("-o", "--ofile"):
            outputFile = arg
        elif opt in ("-c", "--collection"):
            collection = arg.split(",")

    if databaseFile is None or outputFile is None:
        print("Usage: " + clihelp)
        sys.exit(2)

    if not(os.path.isfile(databaseFile)):
        print("ERROR: database not found")
        sys.exit(2)

    db = create_connection(databaseFile)
    with open(outputFile, 'w', encoding='utf8') as f:
        writeHeader(f, title)
        writeMoviesImageTitle(db, f, collection)
        writeMoviesDetail(db, f, collection)
        writeActorsDetail(db, f, collection)
        writeFooter(f)
