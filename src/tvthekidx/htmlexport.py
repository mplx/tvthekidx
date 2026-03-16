# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2025 developer@mplx.eu

from . import database, tags
from . utility import include_image
from . _version import __version__

import datetime
import base64
import os


def helprow(f, key_html, desc):
    f.write('<div class="row mb-2">')
    f.write(f'<div class="col-4 text-end">{key_html}</div>')
    f.write(f'<div class="col-8">{desc}</div>')
    f.write('</div>\n')

def writeHeader(f, title="TVThek Index"):
    now = datetime.datetime.now()
    f.write('<!DOCTYPE html>\n')
    f.write('<html lang="de">\n')
    f.write('<head>\n')
    f.write('   <meta charset="utf-8"/>\n')
    f.write('   <meta name="viewport" content="width=device-width, initial-scale=1.0">\n')
    f.write('   <meta name="generator" content="TVThe(k)Idx v' + __version__ + '" />\n')
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
    f.write('       .origtitle { font-size: 0.5em; }\n')
    f.write('       .fixed-badge        { display: inline-block; text-align: left; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: middle; }\n')
    f.write('       .fixed-badge.fw-80  { width:  80px; }\n')
    f.write('       .fixed-badge.fw-100 { width: 100px; }\n')
    f.write('       .fixed-badge.fw-120 { width: 120px; }\n')
    f.write('       .fixed-badge.fw-160 { width: 160px; }\n')
    #f.write('       .row { outline: 1px dashed red; } .col, [class^="col-"] { outline: 1px dashed blue; background-color: rgba(0, 123, 255, 0.1); }\n') # debug bootstrap
    #f.write('       .row { content-visibility: auto; contain-intrinsic-size: 300px; }\n')
    f.write('       .spin-once { animation: spinOnce 0.25s ease-out; display: inline-block; }\n')
    f.write('       @keyframes spinOnce { 0%   { transform: scale(1); } 50%  { transform: scale(1.15); } 100% { transform: scale(1); } }\n')
    f.write('       .kbd-key { display: inline-block; padding: 2px 6px; margin: 0 2px; font-size: 0.85rem; font-family: monospace; border: 1px solid #ccc; border-radius: 4px; background: #f8f9fa; box-shadow: 0 1px 0 #ccc; }')
    f.write('   </style\n')
    f.write('</head>\n')
    f.write('<body>\n')
    f.write('<nav class="navbar navbar-expand-lg fixed-top navbar-light bg-light">')
    f.write('   <div class="container-fluid">')
    f.write('       <a class="navbar-brand" href="#">' + title + '</a>')
    f.write('       <div class="collapse navbar-collapse" id="navbarSupportedContent">')
    f.write('           <ul class="navbar-nav me-auto mb-2 mb-lg-0">')
    f.write('               <li class="nav-item"><a class="nav-link" href="#new">Neu</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#top">Top</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#index">Medien</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#person">Menschen</a></li>')
    f.write('               <li class="nav-item"><a class="nav-link" href="#tag">Tags</a></li>')
    f.write('           </ul>')
    f.write('           <form class="d-flex" role="search" onsubmit="return false;">')
    f.write('               <div id="spinner" class="spinner-grow text-secondary" role="status"><span class="visually-hidden"></span></div>')
    f.write('               <input id="searchInput" class="form-control me-1" type="search" placeholder="Suche" aria-label="Titel">')
    f.write('           </form>')
#    f.write('           <span class="navbar-text">Stand: ' + now.strftime("%d.%m.%Y") + '</span>')
    f.write('           <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-toggle="modal" data-bs-target="#helpModal">  ?  </button>\n')
    f.write('       </div>')
    f.write('   </div>')
    f.write('</nav>\n')
    f.write('<div class="container">\n')
    f.write('<div class="modal fade" id="helpModal" tabindex="-1" aria-hidden="true"><div class="modal-dialog"><div class="modal-content">\n')
    f.write('<div class="modal-header"><h5 class="modal-title">Index ' + now.strftime("%d.%m.%Y") + '</h5><button type="button" class="btn-close" data-bs-dismiss="modal"></button></div><div class="modal-body">\n')
    helprow(f, '<span class="kbd-key">?</span>', 'Hilfe')
    helprow(f, '<span class="kbd-key">F3</span>', 'Suche')
    helprow(f, '<span class="kbd-key">STRG</span> + <span class="kbd-key">K</span>', 'Suche')
    helprow(f, '<span class="kbd-key">g</span> → <span class="kbd-key">a-z</span>', 'Gehe zu A, B, ..., Z')
    helprow(f, '<span class="kbd-key">s</span>', 'Suche')
    helprow(f, '<span class="kbd-key">ESC</span>', 'Suche beenden')
    f.write('</div></div></div></div>\n')


def writeFooter(f):
    f.write('</div>\n')
    f.write('<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p" crossorigin="anonymous"></script>\n')
    f.write('''<script>
        function copyToClipboard(text, el) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    console.log(text);
                    el.classList.remove('spin-once');
                    void el.offsetWidth;
                    el.classList.add('spin-once');
                    el.addEventListener('animationend', () => {
                        el.classList.remove('spin-once');
                    }, { once: true });
                })
                .catch(err => {
                console.error('Failed to copy: ', err);
                });
        }

        function debounce(fn, delay) {
            let timeout;
            return function () {
                clearTimeout(timeout);
                timeout = setTimeout(() => fn.apply(this, arguments), delay);
            };
        }

        var TVAPP = {};

        async function handleSearch() {
            const start = performance.now();
            const searchTerm = searchInput.value.trim().toLowerCase();

            document.getElementById("spinner").style.visibility = 'visible';
            await new Promise(resolve => setTimeout(resolve, 10));

            if (searchTerm.length === 0) {
                document.getElementById("top").removeAttribute("hidden");
                document.getElementById("top1").removeAttribute("hidden");
                document.getElementById("new").removeAttribute("hidden");
                document.getElementById("new1").removeAttribute("hidden");
                document.getElementById("person").removeAttribute("hidden");
                document.getElementById("persons").removeAttribute("hidden");
                document.getElementById("tag").removeAttribute("hidden");
                document.getElementById("tags").removeAttribute("hidden");
            } else {
                document.getElementById("top").setAttribute("hidden", "hidden");
                document.getElementById("top1").setAttribute("hidden", "hidden");
                document.getElementById("new").setAttribute("hidden", "hidden");
                document.getElementById("new1").setAttribute("hidden", "hidden");
                document.getElementById("person").setAttribute("hidden", "hidden");
                document.getElementById("persons").setAttribute("hidden", "hidden");
                document.getElementById("tag").setAttribute("hidden", "hidden");
                document.getElementById("tags").setAttribute("hidden", "hidden");
            }

            TVAPP.cntFound = 0;
            TVAPP.cntNotFound = 0;

            const imgs = document.querySelectorAll('#movies img');
            imgs.forEach(img => img.style.visibility = 'hidden');

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

            imgs.forEach(img => img.style.visibility = '');

            if (TVAPP.cntFound == 0) {
                document.getElementById("moviecounter").innerHTML = 'keine Filme gefunden';
            } else if (TVAPP.cntNotFound == 0) {
                document.getElementById("moviecounter").innerHTML = TVAPP.cntFound + ' Filme gelistet';
            } else {
                document.getElementById("moviecounter").innerHTML = TVAPP.cntFound + ' / ' + (TVAPP.cntFound+TVAPP.cntNotFound) + ' Filme gefunden';
            }

            document.getElementById("spinner").style.visibility = 'hidden';
            const end = performance.now();
            console.log("Search took", (end - start).toFixed(2), "ms");
        }

        const searchInput = document.getElementById('searchInput');
        const rows = document.querySelectorAll('#movies .row');

        searchInput.addEventListener('input', debounce(handleSearch, 800));
        searchInput.addEventListener('focus', function() { this.select(); });

        window.addEventListener("keydown", (e) => {
          if (e.code === 'F3' || ((e.ctrlKey || e.metaKey) && e.code === 'KeyK')) {
            e.preventDefault();
            searchInput.focus();
          }
        })

        document.getElementById("spinner").style.visibility = 'hidden';

        document.addEventListener("DOMContentLoaded", () => {
            let awaitingSecondKey = false;
            window.addEventListener("keydown", (e) => {
                const key = e.key.toLowerCase();
                const target = e.target;
                const search = document.querySelector("#searchInput");
                // console.log("key:", e.key, "code:", e.code, "shift:", e.shiftKey);
                // --- Escape clears search + retrigger handleSearch
                if (e.code === "Escape") {
                    if (search) {
                        search.value = "";
                        search.dispatchEvent(new Event("input", { bubbles: true }));
                    }
                    search.blur();
                    return;
                }
                // --- Ignore shortcuts if typing in input/textarea
                if (
                    target.tagName === "INPUT" ||
                    target.tagName === "TEXTAREA" ||
                    target.isContentEditable
                ) {
                    return;
                }
                // --- Help
                if (e.key === "?") {
                    const modal = new bootstrap.Modal(document.getElementById("helpModal"));
                    modal.show();
                    return;
                }
                // --- Anchor jump shortcuts
                if (!awaitingSecondKey && key === "g") {
                    awaitingSecondKey = true;
                    setTimeout(() => {
                        awaitingSecondKey = false;
                    }, 1000);
                    return;
                }
                if (awaitingSecondKey) {
                    const targetId = anchorMap[key];
                    if (targetId) {
                        const targetElement = document.querySelector(`#${targetId}`);
                        if (targetElement) {
                            targetElement.scrollIntoView({ behavior: "instant" });
                            history.pushState(null, "", `#${targetId}`);
                        }
                    }
                    awaitingSecondKey = false;
                }
                // --- Search shortcuts
                if (key === "s" || e.code === "F3" || ((e.ctrlKey || e.metaKey) && e.code === "KeyK")) {
                    e.preventDefault();
                    if (search) {
                        search.focus();
                    }
                    return;
                }
            });
        });

        // Enable Bootstrap tooltips
        var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
        var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl)
        })
    </script>\n''')
    f.write('</body>\n')
    f.write('</html>\n')


def writeMoviesImageTitle(db, f, collection, gfxmode):
    whereSql = ""
    if collection:
        if whereSql != "":
            whereSql = whereSql + " AND "
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    f.write('<h3 id="new">Neu</h3>')

    orderBy = "strftime('%Y%m%d', added, 'unixepoch') DESC, score DESC, year DESC, m.title COLLATE NOCASE ASC"
    movies = database.getMovies(db, whereSql, orderBy, "0,45")
    f.write('<section id="new1">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            htmlsrc, htmlwidth, htmlheight = include_image(m['poster'], gfxmode, imgpath, 84, 126)
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"{htmlsrc}\" /></a>"
        else:
            # poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
            poster = "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"
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"84\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
        f.write(f'{posterhtml}')
    f.write('\n</section>\n')

    f.write('<h3 id="top">Top</h3>')

    if whereSql != "":
        whereSql = whereSql + " AND "
    whereSql = whereSql + "NOT (poster IS NULL) AND (score < 100)"
    orderBy = "score DESC, year DESC, m.title COLLATE NOCASE ASC"

    movies = database.getMovies(db, whereSql, orderBy, "0,60")
    f.write('<section id="top1">\n')
    for m in movies:
        id = m['id']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        if m['poster']:
            htmlsrc, htmlwidth, htmlheight = include_image(m['poster'], gfxmode, imgpath, 84, 126)
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"{htmlsrc}\" /></a>"
        else:
            poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
            posterhtml = f"<a href=\"#movie-{id}\"><img width=\"htmlwidth\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
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


def writeMoviesDetail(db, f, collection, gfxmode, urlPrefix):
    f.write('<h3 id="index">Medienverzeichnis</h3>')

    anchor_map = {}

    whereSql = ""
    fileDetail = 0
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
            fileDetail += 1
        whereSql = whereSql[0:-4] + ")"

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    movies = database.getMovies(db, whereSql, "m.title_normalized COLLATE NOCASE ASC, year ASC", None)
    f.write('<section id="movies">')
    for m in movies:
        id = m['id']
        title = m['title']
        title_escaped = m['title'].replace("'", "&#39;").replace('"', "&quot;")
        title_orig = m['title_orig']
        if title:
            first_char = title[0]
            if first_char.isalpha():
                key = first_char.lower()
                if key not in anchor_map:
                    anchor_map[key] = id
        description = m['description'] if m['description'] else ""
        if len(description) > 800:
            description = description[0:800] + "[...]"
        year = m['year']
        tmdbid = m['tmdb_id']
        score = int(m['score'])
        scorecolor = movieRatingColor(score)
        if m['poster']:
            htmlsrc, htmlwidth, htmlheight = include_image(m['poster'], gfxmode, imgpath)
            posterhtml = f"<a href=\"https://www.themoviedb.org/movie/{tmdbid}\"><img title=\"{title}\" width=\"{htmlwidth}\" height=\"{htmlheight}\" src=\"{htmlsrc}\" /></a>"
        else:
            posterhtml = "&nbsp;"
        titleext = ""
        if m["title_orig"] != m['title']:
            titleext = f" <span class='origtitle'>({title_orig})</span>"
        actors = directors = ""
        cast = database.getCast(db, id, "0,15")
        for person in cast:
            actors = actors + '<a href="#person-' + str(person['id']) + '" title="' + str(int(person['popularity'])) + ' Pkt." style="text-decoration:none" class="badge bg-info">' + person['name'] + '</a> '
        crew = database.getCrew(db, id, "job='Director'", "0,15")
        for person in crew:
            directors = directors + '<a href="#person-' + str(person['id']) + '" title="Regie" style="text-decoration:none" class="badge bg-secondary">' + person['name'] + '</a> '
        collectionstr = combinedstr = metadatastr = ""
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
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary fixed-badge fw-100\" style=\"text-decoration:none\" title=\"{col['filename']} [{colsize}]\" href=\"{urlPrefix}{col['filename']}\">{colstr}</a> "
                copyhtmlstr = ""
            else:
                screenshothtml = f"{col['filename']}"
                if col["screenshot"]:
                    screenshot = base64.b64encode(col['screenshot']).decode('ascii')
                    screenshothtml = f"<img alt='Screencapture' src='data:image/png;base64,{screenshot}' />"
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary fixed-badge fw-100\" data-container=\"body\" style=\"text-decoration:none\" href=\"{urlPrefix}{col['filename']}\">{colstr}</a> "
                copyhtmlstr = f"<span class=\"badge bg-secondary\" title=\"Dateinamen kopieren\" onclick=\"copyToClipboard('{col['filename']}', this)\"><span class='icon'>📋 {col['filename']}</span></span> "
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
                        metadatastr = metadatastr + f"<span class=\"badge bg-success fixed-badge fw-100\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {col['width']}x{col['height']}</span> "
                    elif col["width"] >= 1280 or col["height"] >= 720:
                        metadatastr = metadatastr + f"<span class=\"badge bg-secondary fixed-badge fw-100\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {col['width']}x{col['height']}</span> "
                    else:
                        metadatastr = metadatastr + f"<span class=\"badge bg-warning fixed-badge fw-100\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {col['width']}x{col['height']}</span> "
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
            #metadatastr = metadatastr + "<br />"
            combinedstr = combinedstr + collectionstr + metadatastr + copyhtmlstr + "<br />"
            collectionstr = metadatastr = "" # diryt hack to get combinedstr working; replaces collectionstr+metadatastr in future
        if fileDetail == 1:
            collectionstr = f"<dt>Bibliothek</dt><dd>{collectionstr}</dd>"
            metadatastr = f"<dt>Details</dt><dd>{metadatastr}</dd>"
        else:
            collectionstr = f"<dt>Bibliotheken</dt><dd>{collectionstr}</dd>"
            metadatastr = ""
        if description:
            descriptionhtml = f"<p style=\"hyphens: auto; text-align: justify;\">{description}</p>"
        else:
            descriptionhtml = ""
        if titleext:
            titlecombined = title + titleext
        else:
            titlecombined = title
        datastringhtml = f"<p><span class=\"badge bg-secondary\">{year}</span> <span class=\"badge bg-{scorecolor}\">{score}</span> {directors} {actors}</p>"
        f.write(f"""
                <div class="row row-striped p-3" data-search='[{title_escaped}]'>
                    <div class="col-2">{posterhtml}</div>
                    <div class="col-10">
                        <h3 id="movie-{id}">{titlecombined}</h3>
                        <div class="description">
                            {datastringhtml}{descriptionhtml}
                            <p>{combinedstr}</p>
                        </div>
                    </div>
            </div>""")
    cntmovies = len(movies)
    if cntmovies == 1:
        f.write(f"<span id='moviecounter'>{cntmovies} Film gelistet</span>")
    else:
        f.write(f"<span id='moviecounter'>{cntmovies} Filme gelistet</span>")
    f.write('\n</section>\n')

    f.write("\n<script>\n")
    f.write("const anchorMap = {\n")
    for k, v in anchor_map.items():
        f.write(f"  '{k}': 'movie-{v}',\n")
    f.write("};\n")
    f.write("</script>\n")


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


def writeActorsDetail(db, f, collection, gfxmode):
    whereSql = ""
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    actors = database.getActors(db, whereSql)

    f.write('<h3 id="person">Menschen</h3>')
    f.write('<section id="persons">')
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
            htmlsrc, htmlwidth, htmlheight = include_image(a['profile'], gfxmode, imgpath, 38, 59)
            profilehtml = f"<a href=\"https://www.themoviedb.org/person/{tmdbid}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{name}\" src=\"{htmlsrc}\" /></a>"
        else:
            profilehtml = "&nbsp;"
        movies = database.getMoviesByActor(db, id)
        if actorListedChoice(len(movies), popularity):
            i = i + 1
            f.write(f"""
                    <div class="row row-striped p-3" data-search='["{name}"]'>
                        <div class="col"><h4 id="person-{id}">{name}</h4></div>
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
    f.write(f"{i}/{total} Personen gelisted")
    f.write('\n</section>\n')


def writeTagsDetail(db, f, collection):
    whereSql = ""
    if collection:
        whereSql = whereSql + "("
        for col in collection:
            whereSql = whereSql + f"(collection='{col}') OR "
        whereSql = whereSql[0:-4] + ")"

    tags_list = tags.tag_list(db)

    f.write('<h3 id="tag">Tags</h3>')
    f.write('<section id="tags">')

    tcnt = 0
    mcnt = 0

    for t in tags_list:
        tcnt = tcnt + 1
        tagname = t['tag']
        tagid = t['id']
        movies = tags.getMoviesByTagid(db, tagid, whereSql)
        if movies:
            f.write(f"""
                <div class="row row-striped p-3" data-search='["{tagname}"]'>
                    <div class="col-3"><h4 id="person-{tagid}">{tagname}</h4></div>
                    <div class="col-9">
                """)
            for m in movies:
                mcnt = mcnt + 1
                f.write(f"""
                    <a href="#movie-{m['id']}" style="text-decoration:none">
                        <span class="badge bg-secondary">{m['title']}</span>
                    </a>
                """)
            f.write(f"""
                </div></div>
                """)

    if tcnt < 1:
        f.write(f"Keine Tags gefunden.")
    elif mcnt < 1:
        f.write(f"Keine Medien gefunden.")

    f.write('\n</section>\n')
