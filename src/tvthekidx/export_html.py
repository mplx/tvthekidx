# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import argparse
import datetime
import base64
import os
import random

from . import database, tags, tvstation as tvstation_module
from .utility import include_image, verbose
from ._version import __version__


def shorten_middle(s, max_len=55):
    """Shorten a string by replacing the middle with '...', preferring word boundaries."""
    if len(s) <= max_len:
        return s
    words = s.split(' ')
    if len(words) == 1:
        half = (max_len - 3) // 2
        return s[:half] + '...' + s[-(max_len - 3 - half):]
    half = (max_len - 3) // 2
    front_words, front_len = [], 0
    for w in words:
        new_len = front_len + (1 if front_words else 0) + len(w)
        if new_len > half:
            break
        front_words.append(w)
        front_len = new_len
    back_words, back_len = [], 0
    for w in reversed(words):
        new_len = back_len + (1 if back_words else 0) + len(w)
        if new_len > half:
            break
        back_words.insert(0, w)
        back_len = new_len
    if len(front_words) >= len(words) - len(back_words):
        mid = len(words) // 2
        front_words, back_words = words[:mid], words[mid + 1:]
    return ' '.join(front_words) + '... ' + ' '.join(back_words)


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
    # f.write('       .row { outline: 1px dashed red; } .col, [class^="col-"] { outline: 1px dashed blue; background-color: rgba(0, 123, 255, 0.1); }\n')
    # f.write('       .row { content-visibility: auto; contain-intrinsic-size: 300px; }\n')
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
    col_where = ""
    col_params = []
    if collection:
        ph = ",".join("?" * len(collection))
        col_where = f"f.collection_id IN (SELECT id FROM collections WHERE name IN ({ph}))"
        col_params = list(collection)

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    f.write('<h3 id="new">Neu</h3>')

    orderBy = "strftime('%Y%m%d', added, 'unixepoch') DESC, score DESC, year DESC, m.title COLLATE NOCASE ASC"
    movies = database.getMovies(db, col_where or None, orderBy, "0,45", col_params or None)
    poster_map = database.get_movie_attachments_bulk(db, [m['id'] for m in movies], 'poster')
    f.write('<section id="new1">\n')
    for m in movies:
        oid = m['oid']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        poster_list = poster_map.get(m['id'], [])
        poster_data = bytes(poster_list[0]['data']) if poster_list else None
        if poster_data:
            htmlsrc, htmlwidth, htmlheight = include_image(poster_data, gfxmode, imgpath, 84, 126)
            posterhtml = f"<a href=\"#{oid}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"{htmlsrc}\" /></a>"
        else:
            # poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
            poster = "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"
            posterhtml = f"<a href=\"#{oid}\"><img width=\"84\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
        f.write(f'{posterhtml}')
    f.write('\n</section>\n')

    f.write('<h3 id="top">Top</h3>')

    top_where = ("(" + col_where + ") AND " if col_where else "") + "m.id IN (SELECT ref_id FROM attachments WHERE type = 'poster') AND (score < 100)"
    orderBy = "score DESC, year DESC, m.title COLLATE NOCASE ASC"

    movies = database.getMovies(db, top_where, orderBy, "0,60", col_params or None)
    poster_map = database.get_movie_attachments_bulk(db, [m['id'] for m in movies], 'poster')
    f.write('<section id="top1">\n')
    for m in movies:
        oid = m['oid']
        title = m['title']
        year = m['year']
        score = int(m['score'])
        poster_list = poster_map.get(m['id'], [])
        poster_data = bytes(poster_list[0]['data']) if poster_list else None
        if poster_data:
            htmlsrc, htmlwidth, htmlheight = include_image(poster_data, gfxmode, imgpath, 84, 126)
            posterhtml = f"<a href=\"#{oid}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"{htmlsrc}\" /></a>"
        else:
            poster = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="
            posterhtml = f"<a href=\"#{oid}\"><img width=\"htmlwidth\" height=\"{htmlheight}\" title=\"{title} [{year}; {score}%]\" src=\"data:image/png;base64,{poster}\" /></a>"
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

    col_where = ""
    col_params = []
    fileDetail = len(collection) if collection else 0
    if collection:
        ph = ",".join("?" * len(collection))
        col_where = f"f.collection_id IN (SELECT id FROM collections WHERE name IN ({ph}))"
        col_params = list(collection)

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    movies = database.getMovies(db, col_where or None, "m.title_normalized COLLATE NOCASE ASC, year ASC", None, col_params or None)
    movie_ids = [m['id'] for m in movies]
    poster_map = database.get_movie_attachments_bulk(db, movie_ids, 'poster')
    collections_map = database.getCollections_bulk(db, movie_ids)
    cast_map = database.getCast_bulk(db, movie_ids, limit=15)
    crew_map = database.getCrew_bulk(db, movie_ids, "job='Director'", limit=15)
    genre_map = database.getGenres_bulk(db, movie_ids)
    if fileDetail == 1:
        all_file_ids = [col['id'] for cols in collections_map.values() for col in cols]
        screenshot_map = database.get_file_attachments_bulk(db, all_file_ids, 'screenshot')
    else:
        screenshot_map = {}
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
                    anchor_map[key] = m['oid']
        description = m['description'] if m['description'] else ""
        if len(description) > 800:
            description = description[0:800] + "[...]"
        year = m['year']
        tmdbid = m['tmdb_id']
        score = int(m['score'])
        scorecolor = movieRatingColor(score)
        collections = collections_map.get(id, [])
        tvstation_logo_html = ""
        for col in collections:
            if col["tvstation"]:
                logo = tvstation_module.get_logo(col["tvstation"])
                if logo:
                    station_name = tvstation_module.display_name(col["tvstation"])
                    tvstation_logo_html = f'<img src="data:image/png;base64,{logo}" style="float:right;max-height:1em;max-width:53px;opacity:0.5;" title="{station_name}" />'
                    break
        poster_list = poster_map.get(m['id'], [])
        poster_data = bytes(poster_list[0]['data']) if poster_list else None
        if poster_data:
            htmlsrc, htmlwidth, htmlheight = include_image(poster_data, gfxmode, imgpath)
            posterhtml = f"<a href=\"https://www.themoviedb.org/movie/{tmdbid}\"><img title=\"{title}\" width=\"{htmlwidth}\" height=\"{htmlheight}\" src=\"{htmlsrc}\" /></a>"
        else:
            posterhtml = "&nbsp;"
        titleext = ""
        if m["title_orig"] != m['title']:
            titleext = f" <span class='origtitle'>({title_orig})</span>"
        actors = directors = ""
        for person in cast_map.get(id, []):
            actors = actors + '<a href="#' + str(person['oid']) + '" title="' + str(int(person['popularity'])) + ' Pkt." style="text-decoration:none" class="badge bg-info">' + person['name'] + '</a> '
        for person in crew_map.get(id, []):
            directors = directors + '<a href="#' + str(person['oid']) + '" title="Regie" style="text-decoration:none" class="badge bg-secondary">' + person['name'] + '</a> '
        collectionstr = combinedstr = metadatastr = ""
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
                attachments = screenshot_map.get(col["id"], [])
                screenshot_count = len(attachments)
                if attachments:
                    screenshot = base64.b64encode(bytes(random.choice(attachments)["data"])).decode('ascii')
                    screenshothtml = f"<img alt='Screencapture' src='data:image/jpeg;base64,{screenshot}' />"
                collectionstr = collectionstr + f"<a class=\"badge bg-secondary fixed-badge fw-100\" data-container=\"body\" style=\"text-decoration:none\" href=\"{urlPrefix}{col['filename']}\">{colstr}</a> "
                filename_js = col['filename'].replace("\\", "\\\\").replace("'", "\\'")
                copyhtmlstr = f"<span class=\"badge bg-secondary\" title=\"Dateinamen kopieren\" onclick=\"copyToClipboard('{filename_js}', this)\"><span class='icon'>📋 {shorten_middle(col['filename'])}</span></span> "
                metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Größe\">🗎 {colsize}</span> "
                if col['ctime'] > col['added']:
                    metadatastr = metadatastr + f"<span class=\"badge bg-info\" title=\"Datei (Datenbank {dbtime})\">{fctime}</span> "
                else:
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Datei\">{fctime}</span> "
                if col["duration"] is not None:
                    duration = "{:.0f}".format(col['duration'] / 60)
                    metadatastr = metadatastr + f"<span class=\"badge bg-secondary\" title=\"Länge\">🕐 {duration} min</span> "
                if col["width"] is not None:
                    res_label = f"[{screenshot_count}] {col['width']}x{col['height']}" if screenshot_count else f"{col['width']}x{col['height']}"
                    if col["width"] >= 1920 or col["height"] >= 1080:
                        metadatastr = metadatastr + f"<span class=\"badge bg-success fixed-badge fw-120\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {res_label}</span> "
                    elif col["width"] >= 1280 or col["height"] >= 720:
                        metadatastr = metadatastr + f"<span class=\"badge bg-secondary fixed-badge fw-120\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {res_label}</span> "
                    else:
                        metadatastr = metadatastr + f"<span class=\"badge bg-warning fixed-badge fw-120\" title=\"{screenshothtml}\" data-bs-toggle=\"tooltip\" data-bs-html=\"true\">🖵 {res_label}</span> "
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
                if col["tvstation"] is not None:
                    metadatastr = metadatastr + f"<span class=\"badge bg-success\" title=\"TV-Station\">{tvstation_module.display_name(col['tvstation'])}</span> "
            # metadatastr = metadatastr + "<br />"
            combinedstr = combinedstr + collectionstr + metadatastr + copyhtmlstr + "<br />"
            collectionstr = metadatastr = ""  # diryt hack to get combinedstr working; replaces collectionstr+metadatastr in future
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
        genrestr = "".join(f'<span class="badge bg-dark me-1">{g["name"]}</span>' for g in genre_map.get(id, []))
        datastringhtml = f"<p><span class=\"badge bg-secondary\">{year}</span> <span class=\"badge bg-{scorecolor}\">{score}</span> {genrestr} {directors} {actors}</p>"
        f.write(f"""
                <div class="row row-striped p-3" data-search='[{title_escaped}]'>
                    <div class="col-2">{posterhtml}</div>
                    <div class="col-10">
                        <h3 id="{m['oid']}">{tvstation_logo_html}{titlecombined}</h3>
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
        f.write(f"  '{k}': '{v}',\n")
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
    col_where = ""
    col_params = []
    if collection:
        ph = ",".join("?" * len(collection))
        col_where = f"f.collection_id IN (SELECT id FROM collections WHERE name IN ({ph}))"
        col_params = list(collection)

    base = os.path.splitext(os.path.basename(f.name))[0]
    imgdir = f"{base}"
    imgpath = os.path.join(os.path.dirname(f.name), imgdir)

    actors = database.getActors(db, col_where or None, params=col_params or None)
    actor_ids = [a['id'] for a in actors]
    profile_map = database.get_actor_attachments_bulk(db, actor_ids, 'profile')
    movies_by_actor = database.getMoviesByActor_bulk(db, actor_ids)

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
        profile_list = profile_map.get(a['id'], [])
        profile_data = bytes(profile_list[0]['data']) if profile_list else None
        if profile_data:
            htmlsrc, htmlwidth, htmlheight = include_image(profile_data, gfxmode, imgpath, 38, 59)
            profilehtml = f"<a href=\"https://www.themoviedb.org/person/{tmdbid}\"><img width=\"{htmlwidth}\" height=\"{htmlheight}\" title=\"{name}\" src=\"{htmlsrc}\" /></a>"
        else:
            profilehtml = "&nbsp;"
        movies = movies_by_actor.get(id, [])
        if actorListedChoice(len(movies), popularity):
            i = i + 1
            f.write(f"""
                    <div class="row row-striped p-3" data-search='["{name}"]'>
                        <div class="col"><h4 id="{a['oid']}">{name}</h4></div>
                        <div class="col">{profilehtml}</div>
                        <div class="col">{popularityhtml}</div>
                        <div class="col-6"><div class="description">""")
            for m in movies:
                title = m['title']
                year = m['year']
                score = int(m['score'])
                scorecolor = movieRatingColor(m['score'])
                f.write(f'<a href="#{m["oid"]}" style="text-decoration:none" title="{year} / {score}%" class="badge bg-{scorecolor}">{title}</a> ')
            f.write("</div></div></div>")
    f.write(f"{i}/{total} Personen gelisted")
    f.write('\n</section>\n')


def writeTagsDetail(db, f, collection):
    col_where = ""
    col_params = []
    if collection:
        ph = ",".join("?" * len(collection))
        col_where = f"f.collection_id IN (SELECT id FROM collections WHERE name IN ({ph}))"
        col_params = list(collection)

    tags_list = tags.tag_list(db)

    f.write('<h3 id="tag">Tags</h3>')
    f.write('<section id="tags">')

    tcnt = 0
    mcnt = 0

    for t in tags_list:
        tcnt = tcnt + 1
        tagname = t['tag']
        tagid = t['id']
        movies = tags.getMoviesByTagid(db, tagid, col_where or None, col_params or None)
        if movies:
            f.write(f"""
                <div class="row row-striped p-3" data-search='["{tagname}"]'>
                    <div class="col-3"><h4 id="{t['oid']}">{tagname}</h4></div>
                    <div class="col-9">
                """)
            for m in movies:
                mcnt = mcnt + 1
                f.write(f"""
                    <a href="#{m['oid']}" style="text-decoration:none">
                        <span class="badge bg-secondary">{m['title']}</span>
                    </a>
                """)
            f.write("""
                </div></div>
                """)

    if tcnt < 1:
        f.write("Keine Tags gefunden.")
    elif mcnt < 1:
        f.write("Keine Medien gefunden.")

    f.write('\n</section>\n')


# --- Plugin interface ---

def parse_args(remaining):
    parser = argparse.ArgumentParser(prog="tvthekidx export --format html", add_help=False)
    parser.add_argument("--output", "-o", dest="outputFile", default="tvthek.html", help="output file")
    parser.add_argument("--title", "-t", dest="title", default="TVThek Index", help="page title")
    parser.add_argument("--skip-actors", action="store_true", dest="skipActors")
    parser.add_argument("--skip-header", action="store_true", dest="skipHeader")
    parser.add_argument("--graphics", dest="gfxmode", choices=["embed", "reference", "disable"], default="embed")
    parser.add_argument("--url", dest="targetURL", default="./")
    plugin_args, _ = parser.parse_known_args(remaining)
    return plugin_args


def export(db, collection, args, plugin_args):
    with open(plugin_args.outputFile, "w", encoding="utf8") as f:
        verbose(f"Exporting to {plugin_args.outputFile}...", 1)
        writeHeader(f, plugin_args.title)
        if not plugin_args.skipHeader:
            writeMoviesImageTitle(db, f, collection, plugin_args.gfxmode)
        writeMoviesDetail(db, f, collection, plugin_args.gfxmode, plugin_args.targetURL)
        if not plugin_args.skipActors:
            writeActorsDetail(db, f, collection, plugin_args.gfxmode)
        writeTagsDetail(db, f, collection)
        writeFooter(f)
