#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3
import base64
import datetime
import sys
import getopt


def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
    except Error as e:
        print(e)
    else:
        return conn


def writeHeader(f, title = "TVThek Index"):
    now = datetime.datetime.now()
    f.write('<html lang="de">')
    f.write('<header>')
    f.write('<meta charset="utf-8"/>\n')
    f.write('<title>' + title + ' - ' + now.strftime("%d.%m.%Y") + '</title>\n')
    f.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3" crossorigin="anonymous">\n')
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


def getMovies(db, orderby):
    cur = db.cursor()
    selectSQL = f"SELECT m.*, f.filename FROM movies m JOIN files f ON m.id=f.movie_id ORDER BY {orderby}"
    cur.execute(selectSQL)
    return cur.fetchall()


def writeMoviesImageTitle(db, f):
    orderby = "score DESC, year DESC, m.title ASC"
    movies = getMovies(db, orderby + ' LIMIT 0,24')
    f.write('<section id="img1">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"105\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
            f.write(f'{posterhtml}')
    f.write('\n</section>\n')

    movies = getMovies(db, orderby + ' LIMIT 24,126')
    f.write('<section id="img2">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"60\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
            f.write(f'{posterhtml}')
    f.write('\n</section>\n')


def writeMoviesDetail(db, f):
    orderby = "m.title ASC, year ASC"
    idx = 0
    lastyear = 0
    movies = getMovies(db, orderby)
    f.write('<section id="movies">')
    for m in movies:
        id = m['id']
        title = m['title']
        title_orig = m['title_orig']
        filename = m['filename']
        filenamelink = f"<a href=\"{filename}\">{filename}</a>"
        description = m['description']
        year = m['year']
        tmdbid = m['tmdb_id']
        score = int(m['score'])
        scorecolor = "secondary"
        if score<50:
            scorecolor='danger'
        elif score>=70:
            scorecolor='success'
        posterhtml = ""
        if m['poster']:
            poster = base64.b64encode(m['poster']).decode('ascii')
            posterhtml = f"<a href=\"https://www.themoviedb.org/movie/{tmdbid}\"><img title=\"{title}\" src=\"data:image/png;base64,{poster}\" /></a>"
        titleext = ""
        if m["title_orig"] != m['title']:
            titleext = f" <span class='origtitle'>{title_orig}</span>"
        f.write(f"""            
                <div class="row row-striped p-3" id="movie-{id}" data-search='["{title}"]'>
                    <div class="col"><h3>{title}</h3>{titleext}</div>
                    <div class="col">{posterhtml}</div>
                    <div class="col">
                        <dl>
                            <dt>Jahr</dt><dd><span class="badge bg-secondary">{year}</span></dd>
                            <dt>Wertung</dt><dd><span class="badge bg-{scorecolor}">{score}</span></dd>
                            <dt>Datei</dt><dd>{filenamelink}</dd>
                        </dl>
                    </div>
                    <div class="col-6"><div class="description"><p>{description}</p></div></div>
            </div>""")
    f.write('\n</section>\n')


if __name__ == '__main__':

    title = "TVThek Index"
    databaseFile = "tvthek.db"
    outputFile = '_index.html'
    clihelp = sys.argv[0] + ' -v -t <title> -d <dbfile> -o <outputfile>'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvt:d:o:", ["db=","ofile="])
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


    db = create_connection(databaseFile)
    with open(outputFile, 'w') as f:
        writeHeader(f, title)
        writeMoviesImageTitle(db, f)
        writeMoviesDetail(db, f)
        writeFooter(f)
