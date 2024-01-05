# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2024 developer@mplx.eu

import database

import datetime
import base64


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
    f.write('       .tooltip-inner { min-width: 650px; }\n')
    f.write('       .tooltip.show { opacity:1 !important; }\n')
    f.write('       .tooltip-inner { background-color: #606060; }\n')
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
        // Enable Bootstrap tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
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

    movies = database.getMovies(db, whereSql, orderBy, "0,24")
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

    movies = database.getMovies(db, whereSql, orderBy, "24,84")
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
    movies = database.getMovies(db, whereSql, orderBy, "0,84")
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

    movies = database.getMovies(db, whereSql, "m.title COLLATE NOCASE ASC, year ASC", None)
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
        cast = database.getCast(db, id, "0,15")
        for actor in cast:
            actors = actors + '<a href="#actor-' + str(actor['id']) + '" title="' + str(int(actor['popularity'])) + ' Pkt." style="text-decoration:none" class="badge bg-info">' + actor['name'] + '</a> '
        metadatastr = ""
        collectionstr = ""
        collections = database.getCollections(db, id)
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
                filetitlehtml = f"{col['filename']}"
                if col["screenshot"]:
                    screenshot = base64.b64encode(col['screenshot']).decode('ascii')
                    filetitlehtml = f"{col['filename']}<br /><img alt='Screencapture' src='data:image/png;base64,{screenshot}' />"
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary\" data-container=\"body\" style=\"text-decoration:none\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\" title=\"{filetitlehtml}\" href=\"{col['filename']}\">{colstr}</a> "
                metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Größe\">🗎 {colsize}</span> "
                if col['ctime'] > col['added']:
                    metadatastr = metadatastr + f"<span class=\"badge bg-info\" title=\"Datei (Datenbank {dbtime})\">{fctime}</span> "
                else:
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Datei\">{fctime}</span> "
                if col["duration"] is not None:
                    duration = "{:.0f}".format(col['duration'] / 60)
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Länge\">🕐 {duration} min</span> "
                if col["width"] is not None:
                    if col["width"] >= 1920 or col["height"] >= 1080:
                        metadatastr = metadatastr + f"<span class=\"badge bg-success\" title=\"Auflösung\">🖵 {col['width']}x{col['height']}</span> "
                    elif col["width"] >= 1280 or col["height"] >= 720:
                        metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Auflösung\">🖵 {col['width']}x{col['height']}</span> "
                    else:
                        metadatastr = metadatastr + f"<span class=\"badge bg-warning\" title=\"Auflösung\">🖵 {col['width']}x{col['height']}</span> "
                if col["codec"] is not None:
                    if col["codec"] == "hevc":
                        metadatastr = metadatastr + "<span class=\"badge bg-success\" title=\"Codec\">H.265</span> "
                    elif col["codec"] == "h264":
                        metadatastr = metadatastr + "<span class=\"badge bg-secondary\" title=\"Codec\">H.264</span> "
                    else:
                        metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Codec\">{col['codec']}</span> "
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

    actors = database.getActors(db, whereSql)

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
        movies = database.getMoviesByActor(db, id)
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
