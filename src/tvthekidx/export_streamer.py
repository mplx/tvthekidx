# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

# This plugin was coded by Anthropic Sonnet 4.6

import argparse
import base64
import datetime
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
import sys
from urllib.parse import quote as url_quote

from PIL import Image

from . import database, tags
from . import tvstation as tvstation_module
from ._version import __version__
from .utility import verbose

_BS_CSS = 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css'
_BS_CSS_SRI = 'sha384-1BmE4kWBq78iYhFldvKuhfTAU6auU8tT94WrHftjDbrCEXSU1oBoqyl2QvZ6jIW3'
_BS_JS = 'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js'
_BS_JS_SRI = 'sha384-ka7Sk0Gln4gmtz2MlQnikT1wXgYsOg+OMhuP+IlRH9sENBO0LRn5q+8nbTov4+1p'

_CSS = """\
:root {
    --fp-bg:      #0f0f0f;
    --fp-bg2:     #181818;
    --fp-card:    #1e1e1e;
    --fp-card2:   #272727;
    --fp-border:  rgba(255,255,255,.07);
    --fp-text:    #e8e8e8;
    --fp-muted:   #888;
    --fp-accent:  #e50914;
    --fp-radius:  6px;
    --fp-t:       .18s ease;
}
*, *::before, *::after { box-sizing: border-box; }
body {
    background: var(--fp-bg);
    color: var(--fp-text);
    padding-top: 60px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-size: 15px;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
}
a { color: var(--fp-text); text-decoration: none; }
a:hover { color: #fff; }
hr { border-color: #252525; margin: 1.5rem 0; }

/* ── Navbar ───────────────────────────────────────────── */
.fp-navbar {
    background: rgba(10,10,10,.92) !important;
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--fp-border);
    height: 60px;
}
.fp-brand {
    color: var(--fp-accent) !important;
    font-weight: 800;
    font-size: 1.15rem;
    letter-spacing: 2px;
    text-transform: uppercase;
}
.nav-link-fp {
    color: var(--fp-muted);
    font-size: .82rem;
    font-weight: 500;
    padding: 4px 9px;
    border-radius: 4px;
    transition: color var(--fp-t), background var(--fp-t);
}
.nav-link-fp:hover { color: #fff; background: rgba(255,255,255,.08); }

/* ── Section titles ───────────────────────────────────── */
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #fff;
    margin: 2.2rem 0 .6rem;
    padding-left: .75rem;
    border-left: 3px solid var(--fp-accent);
    letter-spacing: .01em;
}

/* ── Horizontal poster row ────────────────────────────── */
.poster-row {
    display: flex;
    overflow-x: auto;
    gap: 14px;
    padding: 6px 2px 18px;
    scrollbar-width: thin;
    scrollbar-color: #3a3a3a transparent;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
}
.poster-row::-webkit-scrollbar { height: 3px; }
.poster-row::-webkit-scrollbar-thumb { background: #3a3a3a; border-radius: 2px; }

/* ── Poster card ──────────────────────────────────────── */
.poster-card { flex: 0 0 auto; scroll-snap-align: start; }
.poster-card a { display: block; position: relative; overflow: hidden; border-radius: var(--fp-radius); }
.poster-card .poster-img {
    display: block;
    object-fit: cover;
    border-radius: var(--fp-radius);
    transition: transform var(--fp-t), box-shadow var(--fp-t), filter var(--fp-t);
}
.poster-card:hover .poster-img {
    transform: scale(1.06) translateY(-3px);
    box-shadow: 0 18px 44px rgba(0,0,0,.85);
    filter: brightness(1.1);
}
/* Hover label overlay */
.poster-card .card-label {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: linear-gradient(transparent, rgba(0,0,0,.88) 45%);
    color: #f0f0f0;
    font-size: .7rem;
    font-weight: 500;
    padding: 32px 8px 8px;
    border-radius: 0 0 var(--fp-radius) var(--fp-radius);
    opacity: 0;
    transition: opacity var(--fp-t);
    line-height: 1.3;
    word-break: break-word;
}
.poster-card:hover .card-label { opacity: 1; }
/* In grids the label is always visible below the image */
.poster-grid .poster-card .card-label,
.person-movies-row .poster-card .card-label {
    position: static;
    background: none;
    padding: .3rem 0 0;
    opacity: 1;
    color: var(--fp-muted);
    font-size: .68rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
/* Placeholder tiles */
.poster-placeholder {
    background: var(--fp-card);
    border: 1px solid rgba(255,255,255,.05);
    border-radius: var(--fp-radius);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: .68rem;
    color: #444;
    text-align: center;
    padding: 8px;
    word-break: break-word;
}

/* ── Person card ──────────────────────────────────────── */
.person-card { flex: 0 0 auto; width: 110px; text-align: center; }
.person-card a { display: block; }
.person-card .person-img {
    width: 92px; height: 92px;
    object-fit: cover;
    border-radius: 50%;
    display: inline-block;
    border: 2px solid #2a2a2a;
    transition: transform var(--fp-t), border-color var(--fp-t), box-shadow var(--fp-t);
}
.person-card:hover .person-img {
    transform: scale(1.1);
    border-color: var(--fp-accent);
    box-shadow: 0 0 0 3px rgba(229,9,20,.25);
}
.person-card .card-label {
    font-size: .72rem;
    font-weight: 500;
    color: var(--fp-muted);
    margin-top: .4rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: color var(--fp-t);
}
.person-card:hover .card-label { color: #fff; }
.person-placeholder {
    width: 92px; height: 92px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1e1e1e, #2a2a2a);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 1.6rem;
    color: #555;
    border: 2px solid #2a2a2a;
}

/* ── Search ───────────────────────────────────────────── */
.search-wrap { max-width: 640px; margin: 2rem auto 1.2rem; }
#search-input {
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.11);
    color: #fff;
    border-radius: 30px;
    padding: .65rem 1.5rem;
    width: 100%;
    font-size: 1rem;
    font-family: inherit;
    outline: none;
    transition: border-color var(--fp-t), background var(--fp-t), box-shadow var(--fp-t);
}
#search-input:focus {
    border-color: rgba(255,255,255,.3);
    background: rgba(255,255,255,.09);
    box-shadow: 0 0 0 3px rgba(229,9,20,.18);
}
#search-input::placeholder { color: #444; }
#search-results { margin-top: .8rem; }
.sr-card {
    display: flex; align-items: center; gap: .9rem;
    background: var(--fp-card);
    border: 1px solid var(--fp-border);
    border-radius: 10px;
    padding: .55rem .9rem;
    margin-bottom: .35rem;
    text-decoration: none !important;
    color: var(--fp-text) !important;
    transition: background var(--fp-t), border-color var(--fp-t), transform var(--fp-t);
}
.sr-card:hover {
    background: var(--fp-card2);
    border-color: rgba(255,255,255,.13);
    transform: translateX(4px);
}
.sr-card img { width: 38px; height: 57px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.sr-name { font-size: .88rem; font-weight: 500; }
.sr-meta { font-size: .71rem; color: var(--fp-muted); margin-top: 1px; }

/* ── Page header (hero backdrop) ─────────────────────── */
.fp-page-header {
    background: linear-gradient(180deg, #1a1a28 0%, var(--fp-bg) 100%);
    padding: 2rem 0 .5rem;
    border-bottom: 1px solid #1e1e1e;
    margin-bottom: 1.5rem;
}

/* ── Hero (movie/person detail) ───────────────────────── */
.fp-hero { display: flex; gap: 2.5rem; align-items: flex-start; flex-wrap: wrap; }
.fp-hero-poster img {
    border-radius: 10px;
    max-height: 370px;
    width: auto;
    display: block;
    box-shadow: 0 24px 64px rgba(0,0,0,.75);
}
.fp-hero-info { flex: 1; min-width: 240px; }
.fp-hero-title {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: .1rem;
    letter-spacing: -.02em;
}
.fp-hero-orig { font-size: .9rem; color: var(--fp-muted); margin-bottom: .65rem; font-style: italic; }
.fp-hero-desc {
    font-size: 1rem;
    color: var(--fp-muted);
    hyphens: auto;
    max-width: 820px;
    margin-top: .75rem;
    line-height: 1.85;
}
.score-chip {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-weight: 700;
    font-size: .78rem;
    color: #fff;
    letter-spacing: .04em;
}
.play-btn {
    display: inline-flex; align-items: center; gap: .5rem;
    background: #fff; color: #000 !important;
    font-weight: 700;
    padding: .5rem 1.6rem;
    border-radius: 6px;
    text-decoration: none !important;
    margin: .8rem 0 .4rem;
    font-size: .95rem;
    transition: background var(--fp-t), transform var(--fp-t);
    letter-spacing: .02em;
}
.play-btn:hover { background: #ddd; transform: scale(1.02); }

/* ── Badges (override Bootstrap defaults) ─────────────── */
.badge { font-weight: 500; letter-spacing: .02em; }
.badge.bg-secondary { background-color: rgba(255,255,255,.1) !important; color: #ccc !important; }
.badge.bg-dark      { background-color: rgba(255,255,255,.07) !important; color: #aaa !important; border: 1px solid rgba(255,255,255,.1); }
.badge.bg-info      { background-color: rgba(100,180,255,.18) !important; color: #7ec8f5 !important; }

/* ── Person chips (cast / crew on movie pages) ────────── */
.fp-person-chip {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: .93rem;
    font-weight: 500;
    margin: 3px 5px 3px 0;
    text-decoration: none !important;
    transition: filter var(--fp-t), transform var(--fp-t);
    line-height: 1.4;
}
.fp-person-chip:hover { filter: brightness(1.25); transform: translateY(-1px); }
.fp-chip-crew { background: rgba(255,255,255,.1); color: #ccc !important; }
.fp-chip-cast { background: rgba(100,180,255,.15); color: #8ed4f8 !important; }
html.fp-light .fp-chip-crew { background: rgba(0,0,0,.08); color: #444 !important; }
html.fp-light .fp-chip-cast { background: rgba(0,100,200,.1); color: #005faa !important; }

/* ── Section sub-headings (Dateien, Ähnliche Filme) ───── */
.fp-section-h5 {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--fp-text);
    margin: 1.4rem 0 .6rem;
    padding-left: .6rem;
    border-left: 2px solid var(--fp-accent);
}

/* ── File info ────────────────────────────────────────── */
.file-info-block {
    background: var(--fp-card);
    border: 1px solid var(--fp-border);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-top: .6rem;
}
.file-collection-name {
    font-size: 1rem;
    font-weight: 600;
    color: var(--fp-text);
    display: flex;
    align-items: center;
    gap: .6rem;
    margin-bottom: .55rem;
}
.file-meta-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: .45rem .6rem;
    margin-bottom: .75rem;
}
.fmi-label {
    font-size: .68rem;
    color: var(--fp-muted);
    text-transform: uppercase;
    letter-spacing: .07em;
    margin-bottom: 1px;
}
.fmi-value {
    font-size: .9rem;
    font-weight: 500;
    color: var(--fp-text);
}
.copy-btn {
    background: none;
    border: 1px solid #3a3a3a;
    color: var(--fp-muted);
    border-radius: 20px;
    padding: 5px 16px;
    cursor: pointer;
    font-size: .85rem;
    font-family: inherit;
    transition: border-color var(--fp-t), color var(--fp-t), background var(--fp-t);
}
.copy-btn:hover { border-color: #888; color: #fff; background: rgba(255,255,255,.05); }
html.fp-light .copy-btn { border-color: #ccc; color: #666; }
html.fp-light .copy-btn:hover { border-color: #888; color: #111; background: rgba(0,0,0,.04); }
.spin-once { animation: spinOnce .25s ease-out; display: inline-block; }
@keyframes spinOnce { 0%{transform:scale(1)} 50%{transform:scale(1.2)} 100%{transform:scale(1)} }

/* ── Screenshot row (movie detail) ──────────────────── */
.fp-screenshot-row {
    display: flex;
    overflow-x: auto;
    gap: 12px;
    padding: 4px 2px 16px;
    scrollbar-width: thin;
    scrollbar-color: #3a3a3a transparent;
}
.fp-screenshot-row::-webkit-scrollbar { height: 3px; }
.fp-screenshot-row::-webkit-scrollbar-thumb { background: #3a3a3a; border-radius: 2px; }
.fp-screenshot, .fp-screenshot-lg {
    flex: 0 0 auto;
    width: auto;
    border-radius: var(--fp-radius);
    display: block;
    transition: transform var(--fp-t), box-shadow var(--fp-t);
}
.fp-screenshot    { height: 180px; }
.fp-screenshot-lg { height: 270px; cursor: zoom-in; }
.fp-screenshot:hover    { transform: scale(1.03); box-shadow: 0 8px 28px rgba(0,0,0,.7); }
.fp-screenshot-lg:hover { transform: scale(1.02); box-shadow: 0 10px 32px rgba(0,0,0,.75); }

/* ── Poster grid (genre/tag pages) ───────────────────── */
.poster-grid { display: flex; flex-wrap: wrap; gap: 18px; padding: .8rem 0 1.5rem; }

/* ── Person movies row ───────────────────────────────── */
.person-movies-row { display: flex; flex-wrap: wrap; gap: 16px; padding: .5rem 0 1rem; }

/* ── TV station cards (index) ────────────────────────── */
.fp-tvstation-card {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: .35rem;
    padding: .6rem .9rem;
    background: var(--fp-card);
    border: 1px solid var(--fp-border);
    border-radius: 8px;
    text-decoration: none !important;
    min-width: 75px;
    transition: background var(--fp-t), border-color var(--fp-t), transform var(--fp-t);
}
.fp-tvstation-card:hover { background: var(--fp-card2); border-color: rgba(255,255,255,.15); transform: translateY(-2px); }
.fp-tvstation-card img  { max-height: 26px; max-width: 90px; opacity: .85; }
.fp-tvstation-card span { font-size: .72rem; color: var(--fp-muted); }
html.fp-light .fp-tvstation-card { background: #fff; border-color: rgba(0,0,0,.1); }
html.fp-light .fp-tvstation-card:hover { background: #f5f5f5; border-color: rgba(0,0,0,.16); }

/* ── Footer ──────────────────────────────────────────── */
footer {
    margin-top: 4rem;
    padding: 2rem 0;
    border-top: 1px solid #1e1e1e;
    color: #3a3a3a;
    font-size: .74rem;
    text-align: center;
    letter-spacing: .04em;
}

/* ── Theme toggle button ─────────────────────────────── */
.fp-theme-btn {
    background: none;
    border: 1px solid rgba(255,255,255,.15);
    color: var(--fp-muted);
    border-radius: 20px;
    padding: 3px 11px;
    cursor: pointer;
    font-size: .88rem;
    font-family: inherit;
    line-height: 1.4;
    transition: border-color var(--fp-t), color var(--fp-t), background var(--fp-t);
}
.fp-theme-btn:hover { border-color: rgba(255,255,255,.3); color: #fff; }

/* ── Light mode ──────────────────────────────────────── */
html.fp-light {
    --fp-bg:     #f2f2f2;
    --fp-bg2:    #e8e8e8;
    --fp-card:   #ffffff;
    --fp-card2:  #efefef;
    --fp-border: rgba(0,0,0,.08);
    --fp-text:   #111111;
    --fp-muted:  #666666;
}
html.fp-light body   { background: var(--fp-bg); color: var(--fp-text); }
html.fp-light a      { color: var(--fp-text); }
html.fp-light a:hover { color: #000; }
html.fp-light hr     { border-color: #d5d5d5; }
html.fp-light .fp-navbar { background: rgba(250,250,250,.93) !important; border-bottom-color: rgba(0,0,0,.1); }
html.fp-light .section-title { color: #111; }
html.fp-light .nav-link-fp { color: #555; }
html.fp-light .nav-link-fp:hover { color: #000; background: rgba(0,0,0,.06); }
html.fp-light .fp-theme-btn { border-color: rgba(0,0,0,.15); color: #666; }
html.fp-light .fp-theme-btn:hover { border-color: rgba(0,0,0,.3); color: #000; background: rgba(0,0,0,.05); }
html.fp-light .poster-row { scrollbar-color: #ccc transparent; }
html.fp-light .poster-row::-webkit-scrollbar-thumb { background: #ccc; }
html.fp-light .poster-placeholder { background: #ddd; border-color: rgba(0,0,0,.07); color: #999; }
html.fp-light .person-placeholder { background: linear-gradient(135deg, #ddd, #ccc); border-color: #bbb; color: #888; }
html.fp-light .person-card .person-img { border-color: #ccc; }
html.fp-light #search-input { background: rgba(0,0,0,.05); border-color: rgba(0,0,0,.14); color: #111; }
html.fp-light #search-input:focus { border-color: rgba(0,0,0,.28); background: rgba(0,0,0,.07); box-shadow: 0 0 0 3px rgba(229,9,20,.1); }
html.fp-light #search-input::placeholder { color: #aaa; }
html.fp-light .sr-card { background: #fff; border-color: rgba(0,0,0,.08); color: #111 !important; }
html.fp-light .sr-card:hover { background: #f5f5f5; border-color: rgba(0,0,0,.14); transform: translateX(4px); }
html.fp-light .fp-page-header { background: linear-gradient(180deg, #dde0f0 0%, var(--fp-bg) 100%); border-bottom-color: #d5d5d5; }
html.fp-light .fp-hero-poster img { box-shadow: 0 20px 50px rgba(0,0,0,.18); }
html.fp-light .file-info-block { background: #fff; border-color: rgba(0,0,0,.08); }
html.fp-light .play-btn { background: #111; color: #fff !important; }
html.fp-light .play-btn:hover { background: #333; }
html.fp-light .badge.bg-secondary { background-color: rgba(0,0,0,.09) !important; color: #333 !important; }
html.fp-light .badge.bg-dark { background-color: rgba(0,0,0,.07) !important; color: #444 !important; border-color: rgba(0,0,0,.1); }
html.fp-light .badge.bg-info { background-color: rgba(0,100,200,.1) !important; color: #0066bb !important; }
html.fp-light footer { border-top-color: #d5d5d5; color: #bbb; }

/* ── Person page film list ────────────────────────────────── */
.fp-film-row { display:flex; gap:1rem; align-items:flex-start; }
.fp-film-row > a:first-child { flex-shrink:0; }
.fp-film-body { flex:1; min-width:0; }
.fp-mt-meta  { margin-top:.35rem; }
.fp-mt-btn   { margin-top:.4rem; }
.fp-poster-sm { width:77px; height:115px; object-fit:cover; border-radius:6px; display:block; }
.fp-poster-sm-ph { width:77px; height:115px; font-size:.6rem; }
.fp-portrait-hero { width:138px; height:207px; object-fit:cover; border-radius:50%; border:3px solid #333; display:block; }
.fp-portrait-ph { width:138px !important; height:138px !important; font-size:3rem !important; }
html.fp-light .fp-portrait-hero { border-color:#ccc; }

/* ── Movie detail hero poster ─────────────────────────────── */
.fp-hero-movie-poster { max-height:350px; width:auto; border-radius:6px; display:block; box-shadow:0 24px 64px rgba(0,0,0,.75); }

/* ── Score / play button size variants ───────────────────── */
.score-chip-sm { font-size:.72rem !important; padding:2px 9px !important; }
.play-btn-sm { padding:.35rem 1rem !important; font-size:.82rem !important; margin:.3rem .5rem .3rem 0 !important; }

/* ── Genre sub-heading in index ──────────────────────────── */
.fp-genre-sub { font-size:1rem; margin:.8rem 0 .3rem; }

/* ── Count badge on section headings ─────────────────────── */
.fp-cnt { font-size:.7rem; }

/* ── Filmlist sort buttons (person pages) ────────────────── */
.fp-sort-btn {
    background: none;
    border: 1px solid rgba(255,255,255,.15);
    color: var(--fp-muted);
    border-radius: 12px;
    padding: 2px 10px;
    cursor: pointer;
    font-size: .75rem;
    font-family: inherit;
    transition: border-color var(--fp-t), color var(--fp-t);
    margin-left: .3rem;
}
.fp-sort-btn:hover { border-color: rgba(255,255,255,.3); color: #fff; }
.fp-sort-active { border-color: var(--fp-accent) !important; color: var(--fp-accent) !important; }
html.fp-light .fp-sort-btn { border-color: rgba(0,0,0,.15); color: #666; }
html.fp-light .fp-sort-btn:hover { border-color: rgba(0,0,0,.3); color: #000; }

/* ── Remove text-decoration from link contexts ───────────── */
a.badge { text-decoration:none; }
.section-title a { text-decoration:none; color:inherit; }
.fp-section-h5 a { text-decoration:none; color:inherit; }
.file-collection-name a { text-decoration:none; }
"""

_JS = """\
function copyToClipboard(text, el) {
    navigator.clipboard.writeText(text)
        .then(function() {
            el.classList.remove('spin-once');
            void el.offsetWidth;
            el.classList.add('spin-once');
            el.addEventListener('animationend', function() { el.classList.remove('spin-once'); }, { once: true });
        })
        .catch(function(err) { console.error('copy failed:', err); });
}

(function() {
    var input   = document.getElementById('search-input');
    var results = document.getElementById('search-results');
    var sections = document.getElementById('fp-sections');
    if (!input) return;

    function debounce(fn, ms) {
        var t;
        return function() { clearTimeout(t); t = setTimeout(fn, ms); };
    }

    function render(q) {
        if (!q) {
            results.innerHTML = '';
            results.hidden = true;
            if (sections) sections.hidden = false;
            return;
        }
        if (sections) sections.hidden = true;
        var idx = window.SEARCH_INDEX || [];
        var found = idx.filter(function(it) { return it.q.toLowerCase().indexOf(q) !== -1; }).slice(0, 40);
        if (!found.length) {
            results.innerHTML = '<p style="color:#888;padding:.5rem 0">Keine Ergebnisse.</p>';
            results.hidden = false;
            return;
        }
        results.innerHTML = found.map(function(it) {
            var imgHtml = it.poster
                ? '<img src="' + it.poster + '" alt="">'
                : (it.portrait
                    ? '<img src="' + it.portrait + '" alt="" style="border-radius:50%">'
                    : '<div style="width:36px;height:54px;background:#333;border-radius:3px;flex-shrink:0"></div>');
            var meta = it.type === 'movie' ? (it.year || '') : 'Person';
            return '<a href="' + it.url + '" class="sr-card">'
                + imgHtml
                + '<div><div class="sr-name">' + it.display + '</div>'
                + '<div class="sr-meta">' + meta + '</div></div></a>';
        }).join('');
        results.hidden = false;
    }

    input.addEventListener('input', debounce(function() { render(input.value.trim().toLowerCase()); }, 280));
    input.addEventListener('focus', function() { if (this.value.trim()) render(this.value.trim().toLowerCase()); });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') { input.value = ''; render(''); input.blur(); return; }
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.key === 's' || e.code === 'F3' || ((e.ctrlKey || e.metaKey) && e.code === 'KeyK')) {
            e.preventDefault(); input.focus();
        }
    });
})();

// Theme toggle
(function() {
    function syncBtn() {
        var btn = document.getElementById('fp-theme-btn');
        if (btn) btn.textContent = document.documentElement.classList.contains('fp-light') ? '☽' : '☀';
    }
    window.fpToggleTheme = function() {
        var light = document.documentElement.classList.toggle('fp-light');
        localStorage.setItem('fp-theme', light ? 'light' : 'dark');
        syncBtn();
    };
    syncBtn();
})();

// Filmlist sort (person / genre / random pages)
(function() {
    var defaults = {title: 'asc', year: 'desc', score: 'desc'};
    window.fpSortFilms = function(key, btn) {
        var list = document.getElementById('fp-filmlist');
        if (!list) return;
        var cards = Array.from(list.children);
        document.querySelectorAll('.fp-sort-btn').forEach(function(b) {
            b.classList.remove('fp-sort-active');
            b.textContent = b.dataset.label;
        });
        btn.classList.add('fp-sort-active');
        if (key === 'random') {
            for (var i = cards.length - 1; i > 0; i--) {
                var j = Math.floor(Math.random() * (i + 1));
                var tmp = cards[i]; cards[i] = cards[j]; cards[j] = tmp;
            }
        } else {
            var curDir = btn.dataset.dir || defaults[key];
            var newDir = curDir === 'asc' ? 'desc' : 'asc';
            btn.dataset.dir = newDir;
            btn.textContent = btn.dataset.label + (newDir === 'asc' ? ' ↑' : ' ↓');
            var mul = newDir === 'asc' ? 1 : -1;
            cards.sort(function(a, b) {
                if (key === 'year' || key === 'score') {
                    return mul * (parseFloat(a.dataset[key] || 0) - parseFloat(b.dataset[key] || 0));
                }
                return mul * (a.dataset[key] || '').localeCompare(b.dataset[key] || '', undefined, {sensitivity: 'base'});
            });
        }
        cards.forEach(function(c) { list.appendChild(c); });
    };
})();
"""


# ---------- utility helpers ----------

def _esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')


def shorten_middle(s, max_len=40):
    if len(s) <= max_len:
        return s
    half = (max_len - 3) // 2
    return s[:half] + '...' + s[-(max_len - 3 - half):]


def _score_color(score):
    if score == 0:
        return '#f0ad4e'
    if score < 50:
        return '#dc3545'
    if score >= 70:
        return '#28a745'
    return '#17a2b8'


def _to_data_uri(img_bytes, target_w, target_h, quality=85):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        ow, oh = img.size
        scale = max(target_w / ow, target_h / oh)
        nw, nh = round(ow * scale), round(oh * scale)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = max(0, (nw - target_w) // 2)
        top  = max(0, (nh - target_h) // 2)
        img  = img.crop((left, top, left + target_w, top + target_h))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=quality)
        return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception as e:
        verbose(f"_to_data_uri failed: {e}", 2)
        return ''


def _screenshot_to_data_uri(img_bytes, max_h=360, quality=82):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        w, h = img.size
        if h > max_h:
            img = img.resize((round(w * max_h / h), max_h), Image.Resampling.LANCZOS)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        buf = io.BytesIO()
        img.save(buf, format='WEBP', quality=quality)
        return 'data:image/webp;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')
    except Exception as e:
        verbose(f"_screenshot_to_data_uri failed: {e}", 2)
        return ''


_ENCODE_WORKERS = min(os.cpu_count() or 4, 8)


def _enc_movie_images(args):
    mid, img_bytes = args
    full  = _to_data_uri(img_bytes, 154, 231, quality=85)
    thumb = _to_data_uri(img_bytes,  38,  57, quality=30)
    return mid, full, thumb


def _enc_person_images(args):
    aid, img_bytes = args
    full  = _to_data_uri(img_bytes, 92, 138, quality=85)
    thumb = _to_data_uri(img_bytes, 38,  57, quality=30)
    return aid, full, thumb


def _enc_screenshot_file(args):
    file_id, blobs = args
    uris = [_screenshot_to_data_uri(b) for b in blobs]
    return file_id, [u for u in uris if u]


# ---------- shared page structure ----------

def _head(f, title, assets_rel, version_meta=False):
    f.write(f'<!DOCTYPE html>\n<html lang="de">\n<head>\n')
    f.write(f'  <meta charset="utf-8"/>\n')
    f.write(f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n')
    gen = f'TVThe(k)Idx v{__version__}' if version_meta else 'TVThe(k)Idx'
    f.write(f'  <meta name="generator" content="{gen}">\n')
    f.write(f'  <title>{_esc(title)}</title>\n')
    f.write(f'  <link rel="stylesheet" href="{_BS_CSS}" integrity="{_BS_CSS_SRI}" crossorigin="anonymous">\n')
    f.write(f'  <link rel="stylesheet" href="{assets_rel}assets/style.css">\n')
    f.write('  <script>if(localStorage.getItem("fp-theme")==="light")document.documentElement.classList.add("fp-light");</script>\n')
    f.write('</head>\n<body>\n')


def _navbar(f, brand, home_url, extra_links=None):
    f.write('<nav class="navbar navbar-dark fp-navbar fixed-top"><div class="container-fluid">\n')
    f.write(f'  <a class="navbar-brand fp-brand" href="{home_url}">{_esc(brand)}</a>\n')
    f.write('  <div class="d-flex gap-3 align-items-center">')
    if extra_links:
        for label, url in extra_links:
            f.write(f'<a class="nav-link-fp" href="{url}">{label}</a>')
    f.write('<button id="fp-theme-btn" class="fp-theme-btn" onclick="fpToggleTheme()" title="Erscheinungsbild wechseln">☀</button>')
    f.write('</div>\n')
    f.write('</div></nav>\n')


def _foot(f, assets_rel, search_js=False, timestamp=False):
    f.write(f'<script src="{_BS_JS}" integrity="{_BS_JS_SRI}" crossorigin="anonymous"></script>\n')
    if search_js:
        f.write(f'<script src="{assets_rel}assets/search.js"></script>\n')
    f.write(f'<script src="{assets_rel}assets/app.js"></script>\n')
    if timestamp:
        now = datetime.datetime.now()
        f.write(f'<footer><p>Generiert {now.strftime("%d.%m.%Y %H:%M")}</p></footer>\n')
    f.write('</body>\n</html>\n')


def _pshard(oid):
    """Return the 1-character shard prefix for an OID."""
    return oid[:1]


def _yshard(year):
    """Return the 1-character shard prefix for a year (first digit, e.g. 1990→'1', 2024→'2')."""
    return str(year)[:1]


# ---------- similarity ----------

def _compute_top_similar(movies, genre_map, cast_map, crew_map, tag_by_movie, top_n=10):
    """
    For every movie compute a weighted similarity score against all others and
    return {movie_id: [top_n movie_ids sorted by descending similarity]}.

    Weights:  genres 0.50 · persons 0.20 · tags 0.15 · score proximity 0.15
    """
    genre_sets  = {m['id']: frozenset(g['id'] for g in genre_map.get(m['id'], []))
                   for m in movies}
    person_sets = {m['id']: frozenset(p['id'] for p in
                                      list(cast_map.get(m['id'], [])) +
                                      list(crew_map.get(m['id'], [])))
                   for m in movies}
    tag_sets    = {m['id']: frozenset(tag_by_movie.get(m['id'], set()))
                   for m in movies}
    score_vals  = {m['id']: float(m['score'] or 0) for m in movies}

    result = {}
    for m in movies:
        mid = m['id']
        ga, pa, ta, sa = genre_sets[mid], person_sets[mid], tag_sets[mid], score_vals[mid]
        sims = []
        for other in movies:
            oid = other['id']
            if oid == mid:
                continue
            gb, pb, tb, sb = genre_sets[oid], person_sets[oid], tag_sets[oid], score_vals[oid]

            gu = ga | gb
            genre_sim  = len(ga & gb) / len(gu) if gu else 0.0

            pu = max(len(pa), len(pb))
            person_sim = len(pa & pb) / pu if pu else 0.0

            tu = ta | tb
            tag_sim    = len(ta & tb) / len(tu) if tu else 0.0

            score_sim  = 1.0 - abs(sa - sb) / 100.0

            sim = 0.50 * genre_sim + 0.20 * person_sim + 0.15 * tag_sim + 0.15 * score_sim
            sims.append((sim, oid))

        sims.sort(key=lambda x: -x[0])
        result[mid] = [oid for _, oid in sims[:top_n]]

    return result


def _sort_buttons_html(default='title'):
    """Inline sort-button span for 'Titel / Jahr / Bewertung / Zufall' controls."""
    keys = [('title', 'Titel'), ('year', 'Jahr'), ('score', 'Bewertung'), ('random', 'Zufall')]
    dirs = {'title': 'asc', 'year': 'desc', 'score': 'desc'}
    parts = []
    for key, label in keys:
        active  = ' fp-sort-active' if key == default else ''
        cur_dir = dirs.get(key, '') if key == default else ''
        text    = label + (' ↑' if cur_dir == 'asc' else ' ↓' if cur_dir == 'desc' else '')
        parts.append(
            f'<button class="fp-sort-btn{active}" onclick="fpSortFilms(\'{key}\',this)"'
            f' data-label="{label}" data-dir="{cur_dir}">{text}</button>')
    return '<span style="margin-left:auto;font-weight:400">' + ''.join(parts) + '</span>'


# ---------- card HTML helpers (return strings) ----------

def _poster_card_html(href, img_src, label, width=154, height=231, is_placeholder=False, data_attrs=None):
    if is_placeholder:
        img = f'<div class="poster-placeholder" style="width:{width}px;height:{height}px">{_esc(label[:25])}</div>'
    else:
        img = f'<img src="{img_src}" width="{width}" height="{height}" loading="lazy" class="poster-img" alt="{_esc(label)}">'
    da = (' ' + ' '.join(f'data-{k}="{_esc(str(v))}"' for k, v in data_attrs.items())) if data_attrs else ''
    return f'<div class="poster-card" style="width:{width}px"{da}><a href="{href}">{img}<div class="card-label">{_esc(label)}</div></a></div>'


def _person_card_html(href, img_src, label, is_placeholder=False):
    if is_placeholder:
        initial = label[0].upper() if label else '?'
        img = f'<div class="person-placeholder">{initial}</div>'
    else:
        img = f'<img src="{img_src}" loading="lazy" class="person-img" alt="{_esc(label)}">'
    return f'<div class="person-card"><a href="{href}">{img}<div class="card-label">{_esc(label)}</div></a></div>'


# ---------- page writers ----------

def _write_movie_page(out_path, movie, cast, crew, genres, collections,
                      poster_uri, jellyfin, similar_movies, poster_uri_map,
                      portrait_uri_map=None, screenshot_uris=None):
    oid        = movie['oid']
    title      = movie['title']
    title_orig = movie['title_orig']
    year       = movie['year']
    desc       = (movie['description'] or '')[:800]
    score      = int(movie['score'] or 0)
    tmdb_id    = movie['tmdb_id']

    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, f"{title} ({year})", '../../')
        nav_links = [('← Index', '../../index.html')]
        if tmdb_id:
            nav_links.append(('TMDB ↗', f'https://www.themoviedb.org/movie/{tmdb_id}'))
        _navbar(f, title, '../../index.html', nav_links)
        f.write('<div class="fp-page-header"><div class="container-fluid px-4">\n')
        f.write('<div class="fp-hero">\n')

        # poster
        f.write('<div class="fp-hero-poster">')
        if poster_uri:
            f.write(f'<img src="{poster_uri}" alt="{_esc(title)}" class="fp-hero-movie-poster">')
        else:
            f.write(f'<div class="poster-placeholder" style="width:154px;height:231px">{_esc(title[:30])}</div>')
        f.write('</div>\n')

        # info panel
        f.write('<div class="fp-hero-info">\n')
        f.write(f'<h1 class="fp-hero-title">{_esc(title)}</h1>\n')
        if title_orig and title_orig != title:
            f.write(f'<div class="fp-hero-orig">{_esc(title_orig)}</div>\n')

        if jellyfin:
            jf_url = f"{jellyfin}/web/#/search?query={url_quote(title)}"
            f.write(f'<a href="{jf_url}" class="play-btn" target="_blank">&#9654; Abspielen</a>\n')

        sc = _score_color(score)
        f.write(f'<div class="mt-2 mb-1"><span class="score-chip me-2" style="background:{sc}">{score}%</span>')
        f.write(f'<a href="../../genres/{_yshard(year)}/{year}.html" class="badge bg-secondary me-2">{year}</a>')
        for g in genres:
            f.write(f'<a href="../../genres/{g["oid"]}.html" class="badge bg-dark me-1">{_esc(g["name"])}</a>')
        f.write('</div>\n')

        if desc:
            f.write(f'<p class="fp-hero-desc">{_esc(desc)}</p>\n')

        f.write('</div>\n</div>\n')  # fp-hero-info, fp-hero
        f.write('</div></div>\n')   # fp-page-header inner + outer

        f.write('<div class="container-fluid px-4">\n')

        # directors
        if crew:
            f.write('<h5 class="fp-section-h5">Regie</h5>\n<div class="poster-row">\n')
            for p in crew:
                p_uri = (portrait_uri_map or {}).get(p['id'], '')
                f.write(_person_card_html(
                    f'../../persons/{_pshard(p["oid"])}/{p["oid"]}.html',
                    p_uri, p['name'], is_placeholder=not p_uri) + '\n')
            f.write('</div>\n')

        # cast
        if cast:
            f.write('<h5 class="fp-section-h5">Besetzung</h5>\n<div class="poster-row">\n')
            for p in cast:
                p_uri = (portrait_uri_map or {}).get(p['id'], '')
                f.write(_person_card_html(
                    f'../../persons/{_pshard(p["oid"])}/{p["oid"]}.html',
                    p_uri, p['name'], is_placeholder=not p_uri) + '\n')
            f.write('</div>\n')

        # screenshots — thumbnails linking to the dedicated screenshot page
        if screenshot_uris:
            sc_shard = _pshard(oid)
            sc_page  = f'../../screenshots/{sc_shard}/{oid}.html'
            f.write(f'<h5 class="fp-section-h5"><a href="{sc_page}">Screenshots</a></h5>\n')
            f.write('<div class="fp-screenshot-row">\n')
            for uri in screenshot_uris:
                f.write(f'<a href="{sc_page}">'
                        f'<img src="{uri}" class="fp-screenshot" loading="lazy" alt="Screenshot">'
                        f'</a>\n')
            f.write('</div>\n')

        # file list
        if collections:
            f.write('<h5 class="fp-section-h5">Dateien</h5>\n')
            for col in collections:
                fname    = col['filename']
                fname_js = fname.replace('\\', '\\\\').replace("'", "\\'")
                tvst     = col['tvstation'] or ''

                # collection name + optional TV station logo
                f.write('<div class="file-info-block mb-3">\n')
                f.write('<div class="file-collection-name">')
                f.write(f'{_esc(col["collection"] or "k.A.")}')
                if tvst:
                    logo = tvstation_module.get_logo(tvst)
                    if logo:
                        sname = tvstation_module.display_name(tvst)
                        f.write(f'<img src="data:image/png;base64,{logo}" style="max-height:1.1em;max-width:60px;opacity:.6" title="{_esc(sname)}">')
                f.write('</div>\n')

                # metadata grid
                meta = []
                if col['collection']:
                    meta.append(('Sammlung', col['collection']))
                if col['size']:
                    meta.append(('Größe', f"{col['size']/1024/1024/1024:.2f} GB"))
                if col['duration']:
                    meta.append(('Dauer', f"{col['duration']/60:.0f} min"))
                if col['width']:
                    meta.append(('Auflösung', f"{col['width']}×{col['height']}"))
                if col['codec']:
                    codec_disp = {'hevc': 'H.265', 'h264': 'H.264'}.get(col['codec'], col['codec'].upper())
                    meta.append(('Codec', codec_disp))
                if col['added']:
                    meta.append(('Hinzugefügt', datetime.datetime.fromtimestamp(col['added']).strftime('%d.%m.%Y')))
                if tvst:
                    meta.append(('Sender', tvstation_module.display_name(tvst)))
                if meta:
                    f.write('<div class="file-meta-grid">\n')
                    for lbl, val in meta:
                        f.write(f'  <div><div class="fmi-label">{lbl}</div><div class="fmi-value">{_esc(val)}</div></div>\n')
                    f.write('</div>\n')

                f.write(f'<button class="copy-btn" onclick="copyToClipboard(\'{fname_js}\',this)">📋 {_esc(shorten_middle(fname, 65))}</button>\n')
                f.write('</div>\n')

        # similar movies
        if similar_movies:
            f.write('<h5 class="fp-section-h5">Ähnliche Filme</h5>\n<div class="poster-row">\n')
            for sm in similar_movies:
                sm_oid  = sm['oid']
                sm_uri  = poster_uri_map.get(sm['id'], '')
                f.write(_poster_card_html(f'../{_pshard(sm_oid)}/{sm_oid}.html',
                                          sm_uri,
                                          f"{sm['title']} ({sm['year']})",
                                          is_placeholder=not sm_uri) + '\n')
            f.write('</div>\n')

        f.write('</div>\n')  # container-fluid
        _foot(f, '../../')


def _write_person_page(out_path, actor, portrait_uri, movies, poster_uri_map,
                       collections_map=None, jellyfin=None):
    oid     = actor['oid']
    name    = actor['name']
    pop     = int(actor['popularity'] or 0)
    tmdb_id = actor['tmdb_id']

    movies_sorted = sorted(movies, key=lambda m: (-(m['year'] or 0), (m['title'] or '').upper()))

    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, name, '../../')
        nav_links = [('← Index', '../../index.html')]
        if tmdb_id:
            nav_links.append(('TMDB ↗', f'https://www.themoviedb.org/person/{tmdb_id}'))
        _navbar(f, name, '../../index.html', nav_links)
        f.write('<div class="fp-page-header"><div class="container-fluid px-4">\n')
        f.write('<div class="fp-hero">\n')

        f.write('<div class="fp-hero-poster">')
        if portrait_uri:
            f.write(f'<img src="{portrait_uri}" alt="{_esc(name)}" class="fp-portrait-hero">')
        else:
            initial = name[0].upper() if name else '?'
            f.write(f'<div class="person-placeholder fp-portrait-ph">{initial}</div>')
        f.write('</div>\n')

        f.write('<div class="fp-hero-info">\n')
        f.write(f'<h1 class="fp-hero-title">{_esc(name)}</h1>\n')
        if pop:
            f.write(f'<div class="text-muted" style="font-size:.85rem">Popularität: {pop}</div>\n')
        f.write('</div>\n</div>\n')  # fp-hero-info, fp-hero
        f.write('</div></div>\n')   # fp-page-header inner + outer

        f.write('<div class="container-fluid px-4">\n')
        if movies_sorted:
            f.write(
                f'<h5 class="fp-section-h5" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
                f'Filme <span class="badge bg-secondary fp-cnt">{len(movies_sorted)}</span>'
                f'{_sort_buttons_html("year")}</h5>\n'
            )
            f.write('<div id="fp-filmlist">\n')
            for m in movies_sorted:
                m_oid   = m['oid']
                m_href  = f'../../media/{_pshard(m_oid)}/{m_oid}.html'
                m_uri   = poster_uri_map.get(m['id'], '')
                score   = int(m['score'] or 0)
                sc_col  = _score_color(score)
                cols    = (collections_map or {}).get(m['id'], [])

                f.write(f'<div class="file-info-block mb-3" data-title="{_esc(m["title"] or "")}" data-year="{m["year"] or 0}" data-score="{score}">\n')
                f.write('<div class="fp-film-row">\n')

                # poster
                f.write(f'<a href="{m_href}">')
                if m_uri:
                    f.write(f'<img src="{m_uri}" class="fp-poster-sm" alt="">')
                else:
                    f.write(f'<div class="poster-placeholder fp-poster-sm-ph">{_esc(m["title"][:20])}</div>')
                f.write('</a>\n')

                # info
                f.write('<div class="fp-film-body">\n')
                f.write(f'<div class="file-collection-name">'
                        f'<span class="score-chip score-chip-sm me-2" style="background:{sc_col}">{score}%</span>'
                        f'<a href="{m_href}">{_esc(m["title"])} ({m["year"]})</a>'
                        f'</div>\n')

                for col in cols:
                    fname    = col['filename']
                    fname_js = fname.replace('\\', '\\\\').replace("'", "\\'")
                    tvst     = col['tvstation'] or ''

                    meta = []
                    if col['size']:
                        meta.append(('Größe',      f"{col['size']/1024/1024/1024:.2f} GB"))
                    if col['duration']:
                        meta.append(('Dauer',      f"{col['duration']/60:.0f} min"))
                    if col['width']:
                        meta.append(('Auflösung',  f"{col['width']}×{col['height']}"))
                    if col['codec']:
                        meta.append(('Codec',      {'hevc': 'H.265', 'h264': 'H.264'}.get(col['codec'], col['codec'].upper())))
                    if col['added']:
                        meta.append(('Hinzugefügt', datetime.datetime.fromtimestamp(col['added']).strftime('%d.%m.%Y')))
                    if col['collection']:
                        meta.append(('Sammlung',   col['collection']))
                    if tvst:
                        meta.append(('TV Sender',  tvstation_module.display_name(tvst)))
                    if meta:
                        f.write('<div class="file-meta-grid fp-mt-meta">\n')
                        for lbl, val in meta:
                            f.write(f'  <div><div class="fmi-label">{lbl}</div><div class="fmi-value">{_esc(val)}</div></div>\n')
                        f.write('</div>\n')
                    f.write('<div class="fp-mt-btn">')
                    if jellyfin:
                        jf_url = f"{jellyfin}/web/#/search?query={url_quote(m['title'])}"
                        f.write(f'<a href="{jf_url}" class="play-btn play-btn-sm" target="_blank">&#9654; Abspielen</a>')
                    f.write(f'<button class="copy-btn" onclick="copyToClipboard(\'{fname_js}\',this)">📋 {_esc(shorten_middle(fname, 55))}</button>')
                    f.write('</div>\n')

                f.write('</div>\n')  # info
                f.write('</div>\n')  # flex
                f.write('</div>\n')  # file-info-block
            f.write('</div>\n')  # fp-filmlist

        f.write('</div>\n')
        _foot(f, '../../')


def _write_genre_page(out_path, genre_name, movies, poster_uri_map):
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, genre_name, '../')
        _navbar(f, genre_name, '../index.html', [('← Index', '../index.html')])
        f.write('<div class="container-fluid px-4 mt-4 pt-2">\n')
        f.write(
            f'<h2 class="section-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
            f'{_esc(genre_name)} <span class="badge bg-secondary fp-cnt">{len(movies)}</span>'
            f'{_sort_buttons_html("title")}</h2>\n'
        )
        if movies:
            f.write('<div id="fp-filmlist" class="poster-grid">\n')
            for m in movies:
                m_oid = m['oid']
                m_uri = poster_uri_map.get(m['id'], '')
                f.write(_poster_card_html(f'../media/{_pshard(m_oid)}/{m_oid}.html',
                                          m_uri,
                                          f"{m['title']} ({m['year']})",
                                          width=120, height=180,
                                          is_placeholder=not m_uri,
                                          data_attrs={'title': m['title'] or '', 'year': m['year'] or 0, 'score': int(m['score'] or 0)}) + '\n')
            f.write('</div>\n')
        else:
            f.write('<p class="text-muted">Keine Medien gefunden.</p>\n')
        f.write('</div>\n')
        _foot(f, '../')


def _write_year_page(out_path, year, movies, poster_uri_map):
    title = str(year)
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, title, '../../')
        _navbar(f, title, '../../index.html', [('← Index', '../../index.html')])
        f.write('<div class="container-fluid px-4 mt-4 pt-2">\n')
        f.write(
            f'<h2 class="section-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
            f'{title} <span class="badge bg-secondary fp-cnt">{len(movies)}</span>'
            f'{_sort_buttons_html("title")}</h2>\n'
        )
        if movies:
            f.write('<div id="fp-filmlist" class="poster-grid">\n')
            for m in movies:
                m_oid = m['oid']
                m_uri = poster_uri_map.get(m['id'], '')
                f.write(_poster_card_html(
                    f'../../media/{_pshard(m_oid)}/{m_oid}.html',
                    m_uri,
                    f"{m['title']} ({m['year']})",
                    width=120, height=180,
                    is_placeholder=not m_uri,
                    data_attrs={'title': m['title'] or '', 'year': m['year'] or 0, 'score': int(m['score'] or 0)}) + '\n')
            f.write('</div>\n')
        else:
            f.write('<p class="text-muted">Keine Medien gefunden.</p>\n')
        f.write('</div>\n')
        _foot(f, '../../')


def _write_tag_page(out_path, tag_name, movies, poster_uri_map, movie_by_id):
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, tag_name, '../')
        _navbar(f, tag_name, '../index.html', [('← Index', '../index.html')])
        f.write('<div class="container-fluid px-4 mt-4 pt-2">\n')
        f.write(
            f'<h2 class="section-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
            f'{_esc(tag_name)} <span class="badge bg-secondary fp-cnt">{len(movies)}</span>'
            f'{_sort_buttons_html("title")}</h2>\n'
        )
        if movies:
            f.write('<div id="fp-filmlist" class="poster-grid">\n')
            for m in movies:
                m_oid  = m['oid']
                m_full = movie_by_id.get(m['id'])
                year   = m_full['year'] if m_full else 0
                score  = int(m_full['score'] or 0) if m_full else 0
                m_uri  = poster_uri_map.get(m['id'], '')
                f.write(_poster_card_html(f'../media/{_pshard(m_oid)}/{m_oid}.html',
                                          m_uri,
                                          f"{m['title']} ({year})" if year else m['title'],
                                          width=120, height=180,
                                          is_placeholder=not m_uri,
                                          data_attrs={'title': m['title'] or '', 'year': year, 'score': score}) + '\n')
            f.write('</div>\n')
        else:
            f.write('<p class="text-muted">Keine Medien gefunden.</p>\n')
        f.write('</div>\n')
        _foot(f, '../')


def _write_screenshot_page(out_path, movie_title, movie_oid, file_screenshot_list):
    """Write screenshots/<shard>/<movie_oid>.html.
    file_screenshot_list: [(file_row, [data_uri, ...]), ...]
    Images are embedded as base64 data URIs.
    """
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, f"{movie_title} — Screenshots", '../../')
        _navbar(f, movie_title, '../../index.html',
                [('← Film', f'../../media/{_pshard(movie_oid)}/{movie_oid}.html'), ('← Index', '../../index.html')])
        f.write('<div class="container-fluid px-4 mt-4 pt-2">\n')
        f.write(f'<h2 class="fp-hero-title mb-3">{_esc(movie_title)} <span style="font-weight:400;font-size:1rem;color:var(--fp-muted)">Screenshots</span></h2>\n')
        for col, sc_uris in file_screenshot_list:
            label = f"{col['collection'] or 'k.A.'} — {col['filename']}"
            f.write(f'<h5 class="fp-section-h5">{_esc(label)}</h5>\n')
            f.write('<div class="fp-screenshot-row">\n')
            for uri in sc_uris:
                f.write(f'<a href="{uri}" target="_blank">'
                        f'<img src="{uri}" class="fp-screenshot-lg" loading="lazy" alt="Screenshot">'
                        f'</a>\n')
            f.write('</div>\n')
        f.write('</div>\n')
        _foot(f, '../../')


def _write_tvstation_page(out_path, station_key, movies, poster_uri_map):
    display = tvstation_module.display_name(station_key)
    logo    = tvstation_module.get_logo(station_key)
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, display, '../')
        _navbar(f, display, '../index.html', [('← Index', '../index.html')])
        f.write('<div class="fp-page-header"><div class="container-fluid px-4">\n')
        f.write('<div class="fp-hero">\n')
        if logo:
            f.write(f'<div class="fp-hero-poster"><img src="data:image/png;base64,{logo}" alt="{_esc(display)}" style="max-height:80px;width:auto;border-radius:4px;opacity:.9;filter:brightness(1.1)"></div>\n')
        f.write(
            f'<div class="fp-hero-info">'
            f'<h1 class="fp-hero-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
            f'{_esc(display)} <span class="badge bg-secondary ms-2 fp-cnt">{len(movies)}</span>'
            f'{_sort_buttons_html("title")}</h1></div>\n'
        )
        f.write('</div>\n')
        f.write('</div></div>\n')
        f.write('<div class="container-fluid px-4">\n')
        if movies:
            f.write('<div id="fp-filmlist" class="poster-grid">\n')
            for m in movies:
                m_oid = m['oid']
                m_uri = poster_uri_map.get(m['id'], '')
                f.write(_poster_card_html(f'../media/{_pshard(m_oid)}/{m_oid}.html',
                                          m_uri,
                                          f"{m['title']} ({m['year']})",
                                          width=120, height=180,
                                          is_placeholder=not m_uri,
                                          data_attrs={'title': m['title'] or '', 'year': m['year'] or 0, 'score': int(m['score'] or 0)}) + '\n')
            f.write('</div>\n')
        else:
            f.write('<p class="text-muted">Keine Medien gefunden.</p>\n')
        f.write('</div>\n')
        _foot(f, '../')


def _write_list_page(out_path, page_title, movies, poster_uri_map, sortable=False, default_sort='title'):
    """Root-level (depth 0) full-list page — used for Neu/Top/Random overviews."""
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, page_title, '')
        _navbar(f, page_title, 'index.html', [('← Index', 'index.html')])
        f.write('<div class="container-fluid px-4 mt-4 pt-2">\n')
        if sortable:
            f.write(
                f'<h2 class="section-title" style="display:flex;align-items:center;flex-wrap:wrap;gap:.3rem">'
                f'{_esc(page_title)} <span class="badge bg-secondary fp-cnt">{len(movies)}</span>'
                f'{_sort_buttons_html(default_sort)}</h2>\n'
            )
        else:
            f.write(f'<h2 class="section-title">{_esc(page_title)} <span class="badge bg-secondary fp-cnt">{len(movies)}</span></h2>\n')
        if movies:
            grid_id = ' id="fp-filmlist"' if sortable else ''
            f.write(f'<div class="poster-grid"{grid_id}>\n')
            for m in movies:
                m_oid = m['oid']
                m_uri = poster_uri_map.get(m['id'], '')
                da = {'title': m['title'] or '', 'year': m['year'] or 0, 'score': int(m['score'] or 0)} if sortable else None
                f.write(_poster_card_html(f'media/{_pshard(m_oid)}/{m_oid}.html',
                                          m_uri,
                                          f"{m['title']} ({m['year']})",
                                          width=120, height=180,
                                          is_placeholder=not m_uri,
                                          data_attrs=da) + '\n')
            f.write('</div>\n')
        else:
            f.write('<p class="text-muted">Keine Medien gefunden.</p>\n')
        f.write('</div>\n')
        _foot(f, '')


def _write_search_js(targetpath, search_index_json):
    with open(os.path.join(targetpath, 'assets', 'search.js'), 'w', encoding='utf-8') as f:
        f.write(f'window.SEARCH_INDEX = {search_index_json};\n')


def _write_index(out_path, targetpath, title,
                 newest_movies, top_movies, random_movies,
                 top_genres, genre_newest,
                 popular_persons, newest_persons, random_persons,
                 all_genres, all_tags, all_years,
                 poster_uri_map, portrait_uri_map,
                 tvstations=None):
    with open(out_path, 'w', encoding='utf-8') as f:
        _head(f, title, '', version_meta=True)
        nav_links = [('Zufall', '#fp-random'), ('Neu', '#fp-new'), ('Top', '#fp-top'),
                     ('Genres', '#fp-genres'), ('Künstler', '#fp-persons'), ('Tags', '#fp-tags'),
                     ('Jahre', '#fp-years')]
        if tvstations:
            nav_links.append(('TV-Sender', '#fp-tvstations'))
        _navbar(f, title, 'index.html', nav_links)

        f.write('<div class="container-fluid px-4 mt-2 pt-2">\n')

        # Search
        f.write('<div class="search-wrap">\n')
        f.write('<input id="search-input" type="search" placeholder="Suche nach Titeln, Personen ..." autocomplete="off">\n')
        f.write('<div id="search-results" hidden></div>\n')
        f.write('</div>\n')

        f.write('<div id="fp-sections">\n')

        # Zufall (random movies — top of page)
        if random_movies:
            f.write('<h2 class="section-title" id="fp-random"><a href="random.html">Zufall</a></h2>\n<div class="poster-row">\n')
            for m in random_movies:
                m_uri = poster_uri_map.get(m['id'], '')
                f.write(_poster_card_html(f'media/{_pshard(m["oid"])}/{m["oid"]}.html',
                                          m_uri,
                                          f"{m['title']} ({m['year']})",
                                          is_placeholder=not m_uri) + '\n')
            f.write('</div>\n')

        # Newest
        f.write('<h2 class="section-title" id="fp-new"><a href="new.html">Neu hinzugefügt</a></h2>\n<div class="poster-row">\n')
        for m in newest_movies:
            m_uri = poster_uri_map.get(m['id'], '')
            f.write(_poster_card_html(f'media/{_pshard(m["oid"])}/{m["oid"]}.html',
                                      m_uri,
                                      f"{m['title']} ({m['year']})",
                                      is_placeholder=not m_uri) + '\n')
        f.write('</div>\n')

        # Top
        f.write('<h2 class="section-title" id="fp-top"><a href="top.html">Top bewertet</a></h2>\n<div class="poster-row">\n')
        for m in top_movies:
            m_uri = poster_uri_map.get(m['id'], '')
            sc    = int(m['score'] or 0)
            f.write(_poster_card_html(f'media/{_pshard(m["oid"])}/{m["oid"]}.html',
                                      m_uri,
                                      f"{m['title']} ({m['year']}) {sc}%",
                                      is_placeholder=not m_uri) + '\n')
        f.write('</div>\n')

        # Per-genre carousels
        if top_genres:
            f.write('<h2 class="section-title" id="fp-genres">Genres</h2>\n')
            for g in top_genres:
                gid  = g['id']
                gnm  = g['name']
                goid = g['oid']
                f.write(f'<h4 class="fp-genre-sub"><a href="genres/{goid}.html">{_esc(gnm)}</a></h4>\n')
                f.write('<div class="poster-row">\n')
                for m in genre_newest.get(gid, []):
                    m_uri = poster_uri_map.get(m['id'], '')
                    f.write(_poster_card_html(f'media/{_pshard(m["oid"])}/{m["oid"]}.html',
                                              m_uri,
                                              f"{m['title']} ({m['year']})",
                                              is_placeholder=not m_uri) + '\n')
                f.write('</div>\n')

        # Popular artists
        if popular_persons:
            f.write('<h2 class="section-title" id="fp-persons">Beliebte Künstler</h2>\n<div class="poster-row">\n')
            for a in popular_persons:
                a_uri = portrait_uri_map.get(a['id'], '')
                shard = _pshard(a['oid'])
                f.write(_person_card_html(f'persons/{shard}/{a["oid"]}.html',
                                          a_uri,
                                          a['name'],
                                          is_placeholder=not a_uri) + '\n')
            f.write('</div>\n')

        # Newest artists
        if newest_persons:
            f.write('<h2 class="section-title">Neue Künstler</h2>\n<div class="poster-row">\n')
            for a in newest_persons:
                a_uri = portrait_uri_map.get(a['id'], '')
                shard = _pshard(a['oid'])
                f.write(_person_card_html(f'persons/{shard}/{a["oid"]}.html',
                                          a_uri,
                                          a['name'],
                                          is_placeholder=not a_uri) + '\n')
            f.write('</div>\n')

        # Random artists
        if random_persons:
            f.write('<h2 class="section-title">Zufällige Künstler</h2>\n<div class="poster-row">\n')
            for a in random_persons:
                a_uri = portrait_uri_map.get(a['id'], '')
                shard = _pshard(a['oid'])
                f.write(_person_card_html(f'persons/{shard}/{a["oid"]}.html',
                                          a_uri,
                                          a['name'],
                                          is_placeholder=not a_uri) + '\n')
            f.write('</div>\n')

        # Genres nav
        if all_genres:
            all_genres_sorted = sorted(all_genres, key=lambda g: g['name'].upper())
            f.write('<h2 class="section-title" id="fp-genres-list">Genres</h2>\n<div class="mb-3">\n')
            for g in all_genres_sorted:
                f.write(f'<a href="genres/{g["oid"]}.html" class="badge bg-dark me-1 mb-1" style="font-size:.8rem">{_esc(g["name"])}</a>')
            f.write('\n</div>\n')

        # Veröffentlichung (years) nav
        if all_years:
            f.write('<h2 class="section-title" id="fp-years">Veröffentlichung</h2>\n<div class="mb-3">\n')
            for y in all_years:
                f.write(f'<a href="genres/{_yshard(y)}/{y}.html" class="badge bg-dark me-1 mb-1" style="font-size:.8rem">{y}</a>')
            f.write('\n</div>\n')

        # Tags nav
        if all_tags:
            f.write('<h2 class="section-title" id="fp-tags">Tags</h2>\n<div class="mb-3">\n')
            for t in all_tags:
                f.write(f'<a href="tags/{t["oid"]}.html" class="badge bg-secondary me-1 mb-1" style="font-size:.8rem">{_esc(t["tag"])}</a>')
            f.write('\n</div>\n')

        # TV stations nav
        if tvstations:
            f.write('<h2 class="section-title" id="fp-tvstations">TV-Sender</h2>\n')
            f.write('<div class="d-flex flex-wrap gap-2 mb-3">\n')
            for key in sorted(tvstations, key=lambda k: tvstation_module.display_name(k).upper()):
                disp = tvstation_module.display_name(key)
                logo = tvstation_module.get_logo(key)
                f.write(f'<a href="tvstations/{key}.html" class="fp-tvstation-card">\n')
                if logo:
                    f.write(f'  <img src="data:image/png;base64,{logo}" alt="{_esc(disp)}">\n')
                f.write(f'  <span>{_esc(disp)}</span>\n</a>\n')
            f.write('</div>\n')

        f.write('</div>\n')  # fp-sections
        f.write('</div>\n')  # container

        _foot(f, '', search_js=True, timestamp=True)


# ---------- plugin interface ----------

def parse_args(remaining):
    parser = argparse.ArgumentParser(prog='tvthekidx export --format streamer', add_help=False)
    parser.add_argument('--targetpath', dest='targetpath', required=True,
                        help='output directory')
    parser.add_argument('--jellyfin', dest='jellyfin', default=None,
                        help='Jellyfin base URL, e.g. http://10.1.2.3:8096')
    parser.add_argument('--title', '-t', dest='title', default='TVThek Index',
                        help='site title')
    parser.add_argument('--overwrite', action='store_true', default=False,
                        help='write into an existing directory; skip unchanged image files, always overwrite HTML')
    plugin_args, _ = parser.parse_known_args(remaining)
    return plugin_args


def export(db, collection, args, plugin_args):
    targetpath   = plugin_args.targetpath
    jellyfin     = plugin_args.jellyfin
    title        = plugin_args.title
    overwrite    = plugin_args.overwrite

    if os.path.exists(targetpath) and not overwrite:
        print(f"ERROR: '{targetpath}' already exists (use --overwrite to update in place)")
        sys.exit(2)
    os.makedirs(targetpath, exist_ok=True)
    for sub in ('assets', 'media', 'persons', 'genres', 'tags', 'tvstations'):
        os.makedirs(os.path.join(targetpath, sub), exist_ok=True)

    # --- write static assets ---
    with open(os.path.join(targetpath, 'assets', 'style.css'), 'w', encoding='utf-8') as f:
        f.write(_CSS)
    with open(os.path.join(targetpath, 'assets', 'app.js'), 'w', encoding='utf-8') as f:
        f.write(_JS)

    # --- collection WHERE fragment ---
    col_where = ''
    if collection:
        col_where = '(' + ' OR '.join(f"collection='{c}'" for c in collection) + ')'

    # --- bulk-fetch all data ---
    verbose("Fetching data...", 1)
    movies     = database.getMovies(db, col_where or None,
                                    'm.title_normalized COLLATE NOCASE ASC, year ASC')
    movie_ids  = [m['id'] for m in movies]
    movie_by_id = {m['id']: m for m in movies}

    poster_map      = database.get_movie_attachments_bulk(db, movie_ids, 'poster')
    cast_map        = database.getCast_bulk(db, movie_ids, limit=20)
    crew_map        = database.getCrew_bulk(db, movie_ids, "job='Director'", limit=15)
    genre_map       = database.getGenres_bulk(db, movie_ids)
    collections_map = database.getCollections_bulk(db, movie_ids)

    actors      = database.getActors(db, col_where or None)
    actor_ids   = [a['id'] for a in actors]
    profile_map = database.get_actor_attachments_bulk(db, actor_ids, 'profile')
    movies_by_actor = database.getMoviesByActor_bulk(db, actor_ids)

    # actors with at least 2 movies in the current collection
    qualified_actor_ids = {
        aid for aid in actor_ids
        if sum(1 for m in movies_by_actor.get(aid, []) if m['id'] in movie_by_id) >= 2
    }

    tags_list = tags.tag_list(db)

    # tags per movie (movie_id → set of tag IDs)
    tag_sql = ('SELECT DISTINCT f.movie_id, ft.t_id FROM files_tags ft JOIN files f ON ft.f_id = f.id'
               + (f' WHERE {col_where}' if col_where else ''))
    cur = db.cursor()
    cur.execute(tag_sql)
    tag_by_movie = {}
    for row in cur.fetchall():
        tag_by_movie.setdefault(row[0], set()).add(row[1])

    # --- encode all images in parallel ---
    verbose("Encoding images...", 1)

    referenced_actor_ids = (
        {p['id'] for rows in cast_map.values() for p in rows} |
        {p['id'] for rows in crew_map.values() for p in rows}
    ) & qualified_actor_ids

    poster_uri_map   = {}
    poster_thumb_map = {}
    movie_tasks = [(m['id'], bytes(poster_map[m['id']][0]['data']))
                   for m in movies if poster_map.get(m['id'])]
    with ThreadPoolExecutor(max_workers=_ENCODE_WORKERS) as ex:
        for mid, full, thumb in ex.map(_enc_movie_images, movie_tasks):
            if full:  poster_uri_map[mid]   = full
            if thumb: poster_thumb_map[mid] = thumb

    portrait_uri_map   = {}
    portrait_thumb_map = {}
    person_tasks = [(a['id'], bytes(profile_map[a['id']][0]['data']))
                    for a in actors
                    if a['id'] in referenced_actor_ids and profile_map.get(a['id'])]
    with ThreadPoolExecutor(max_workers=_ENCODE_WORKERS) as ex:
        for aid, full, thumb in ex.map(_enc_person_images, person_tasks):
            if full:  portrait_uri_map[aid]   = full
            if thumb: portrait_thumb_map[aid] = thumb

    # --- encode screenshot images ---
    all_file_ids = [col['id'] for cols in collections_map.values() for col in cols]
    raw_screenshot_map = database.get_file_attachments_bulk(db, all_file_ids, 'screenshot') if all_file_ids else {}
    screenshots_by_file = {}  # file_id → [data_uri, ...]
    sc_tasks = [(fid, [bytes(att['data']) for att in atts])
                for fid, atts in raw_screenshot_map.items()]
    with ThreadPoolExecutor(max_workers=_ENCODE_WORKERS) as ex:
        for file_id, uris in ex.map(_enc_screenshot_file, sc_tasks):
            if uris: screenshots_by_file[file_id] = uris

    # movie_id → [(file_row, [data_uri, ...]), ...] — only files that have screenshots
    movie_screenshot_files = {}
    for mid, cols in collections_map.items():
        for col in cols:
            scs = screenshots_by_file.get(col['id'], [])
            if scs:
                movie_screenshot_files.setdefault(mid, []).append((col, scs))

    # flat list for the thumbnail strip on the movie detail page
    movie_screenshot_data = {
        mid: [sc for _, scs in file_list for sc in scs]
        for mid, file_list in movie_screenshot_files.items()
    }

    # --- movies_by_genre for genre pages ---
    movies_by_genre_id = {}
    for mid, genre_list in genre_map.items():
        for g in genre_list:
            movies_by_genre_id.setdefault(g['id'], []).append(mid)

    # --- inline SQL helpers ---
    cur = db.cursor()

    def _col_and():
        return f' AND {col_where}' if col_where else ''

    def _col_wh():
        return f' WHERE {col_where}' if col_where else ''

    # newest 20 movies
    cur.execute(
        f'SELECT DISTINCT m.id, m.oid, m.title, m.year, m.score '
        f'FROM movies m JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'ORDER BY f.added DESC, m.title COLLATE NOCASE ASC LIMIT 20')
    newest_movies = cur.fetchall()

    # top 20 movies (has poster, score < 100)
    wh = ('WHERE ' if not col_where else f'WHERE {col_where} AND ') + 'm.score < 100 AND EXISTS (SELECT 1 FROM attachments a WHERE a.ref_id=m.id AND a.type=\'poster\')'
    cur.execute(
        f'SELECT DISTINCT m.id, m.oid, m.title, m.year, m.score '
        f'FROM movies m JOIN files f ON f.movie_id = m.id {wh} '
        f'ORDER BY m.score DESC, m.title COLLATE NOCASE ASC LIMIT 20')
    top_movies = cur.fetchall()

    # random 250 movies (first 20 used for the index carousel, all 250 for random.html)
    cur.execute(
        f'SELECT DISTINCT m.id, m.oid, m.title, m.year, m.score '
        f'FROM movies m JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'ORDER BY RANDOM() LIMIT 250')
    random_250   = cur.fetchall()
    random_movies = random_250[:20]

    # newest 250 / top 250 for full-list pages
    cur.execute(
        f'SELECT m.id, m.oid, m.title, m.year, m.score, MAX(f.added) AS last_added '
        f'FROM movies m JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'GROUP BY m.id '
        f'ORDER BY last_added DESC, m.title COLLATE NOCASE ASC LIMIT 250')
    newest_250 = cur.fetchall()

    wh250 = ('WHERE ' if not col_where else f'WHERE {col_where} AND ') + 'm.score < 100'
    cur.execute(
        f'SELECT DISTINCT m.id, m.oid, m.title, m.year, m.score '
        f'FROM movies m JOIN files f ON f.movie_id = m.id {wh250} '
        f'ORDER BY m.score DESC, m.title COLLATE NOCASE ASC LIMIT 250')
    top_250 = cur.fetchall()

    # top 10 genres by movie count
    cur.execute(
        f'SELECT g.id, g.oid, g.name, COUNT(DISTINCT m.id) AS cnt '
        f'FROM genres g '
        f'JOIN movies_genres mg ON g.id = mg.genre_id '
        f'JOIN movies m ON mg.movie_id = m.id '
        f'JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'GROUP BY g.id ORDER BY cnt DESC LIMIT 10')
    top_genres = cur.fetchall()

    # newest 20 movies per top genre (10 queries, one per genre)
    genre_newest = {}
    for g in top_genres:
        and_col = f' AND {col_where}' if col_where else ''
        cur.execute(
            f'SELECT DISTINCT m.id, m.oid, m.title, m.year, m.score '
            f'FROM movies m '
            f'JOIN movies_genres mg ON m.id = mg.movie_id '
            f'JOIN files f ON f.movie_id = m.id '
            f'WHERE mg.genre_id = ?{and_col} '
            f'ORDER BY f.added DESC, m.title COLLATE NOCASE ASC LIMIT 20',
            (g['id'],))
        genre_newest[g['id']] = cur.fetchall()

    # popular 20 persons (actors already sorted by popularity DESC)
    popular_persons = [a for a in actors if a['id'] in qualified_actor_ids][:20]

    # newest 20 persons
    cur.execute(
        f'SELECT DISTINCT a.id, a.oid, a.name, a.popularity, a.tmdb_id '
        f'FROM actors a '
        f'JOIN actors_movies am ON a.id = am.a_id '
        f'JOIN movies m ON am.m_id = m.id '
        f'JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'ORDER BY f.added DESC, a.popularity DESC LIMIT 100')
    newest_persons = [a for a in cur.fetchall() if a['id'] in qualified_actor_ids][:20]

    # random 20 persons
    cur.execute(
        f'SELECT DISTINCT a.id, a.oid, a.name, a.popularity, a.tmdb_id '
        f'FROM actors a '
        f'JOIN actors_movies am ON a.id = am.a_id '
        f'JOIN movies m ON am.m_id = m.id '
        f'JOIN files f ON f.movie_id = m.id{_col_wh()} '
        f'ORDER BY RANDOM() LIMIT 100')
    random_persons = [a for a in cur.fetchall() if a['id'] in qualified_actor_ids][:20]

    # --- compute similarity ---
    verbose("Computing similarity scores...", 1)
    top_similar = _compute_top_similar(movies, genre_map, cast_map, crew_map, tag_by_movie, top_n=20)

    # --- write movie pages ---
    verbose(f"Writing {len(movies)} movie pages...", 1)
    for m in movies:
        mid  = m['id']
        shard_dir = os.path.join(targetpath, 'media', _pshard(m['oid']))
        os.makedirs(shard_dir, exist_ok=True)
        path = os.path.join(shard_dir, f"{m['oid']}.html")
        similar_movies = [movie_by_id[sid] for sid in top_similar.get(mid, []) if sid in movie_by_id]
        qual_cast = sorted(
            [p for p in cast_map.get(mid, []) if p['id'] in qualified_actor_ids],
            key=lambda p: p['name'].upper()
        )
        qual_crew = [p for p in crew_map.get(mid, []) if p['id'] in qualified_actor_ids]
        _write_movie_page(
            path, m, qual_cast, qual_crew,
            genre_map.get(mid, []),
            collections_map.get(mid, []),
            poster_uri_map.get(mid, ''),
            jellyfin, similar_movies,
            poster_uri_map, portrait_uri_map,
            movie_screenshot_data.get(mid, []))

    # --- write screenshot detail pages ---
    sc_page_count = len(movie_screenshot_files)
    if sc_page_count:
        verbose(f"Writing {sc_page_count} screenshot pages...", 1)
        for m in movies:
            file_list = movie_screenshot_files.get(m['id'])
            if not file_list:
                continue
            shard_dir = os.path.join(targetpath, 'screenshots', _pshard(m['oid']))
            os.makedirs(shard_dir, exist_ok=True)
            path = os.path.join(shard_dir, f"{m['oid']}.html")
            _write_screenshot_page(path, m['title'], m['oid'], file_list)

    # --- write person pages ---
    qualified_actors = [a for a in actors if a['id'] in qualified_actor_ids]
    verbose(f"Writing {len(qualified_actors)} person pages...", 1)
    for a in qualified_actors:
        aid       = a['id']
        shard_dir = os.path.join(targetpath, 'persons', _pshard(a['oid']))
        os.makedirs(shard_dir, exist_ok=True)
        path = os.path.join(shard_dir, f"{a['oid']}.html")
        actor_movies = [m for m in movies_by_actor.get(aid, []) if m['id'] in movie_by_id]
        _write_person_page(
            path, a, portrait_uri_map.get(aid, ''), actor_movies, poster_uri_map,
            collections_map=collections_map, jellyfin=jellyfin)

    # --- collect all genres from genre_map ---
    all_genres_dict = {}
    for mid, genre_list in genre_map.items():
        for g in genre_list:
            all_genres_dict[g['id']] = g

    # --- write genre pages ---
    verbose(f"Writing {len(all_genres_dict)} genre pages...", 1)
    for gid, g in all_genres_dict.items():
        genre_movie_ids = movies_by_genre_id.get(gid, [])
        genre_movies = sorted(
            [movie_by_id[mid] for mid in genre_movie_ids if mid in movie_by_id],
            key=lambda m: (m['title_normalized'] or m['title']).upper())
        path = os.path.join(targetpath, 'genres', f"{g['oid']}.html")
        _write_genre_page(path, g['name'], genre_movies, poster_uri_map)

    # --- write year pages ---
    movies_by_year = {}
    for m in movies:
        if m['year']:
            movies_by_year.setdefault(m['year'], []).append(m)
    all_years = sorted(movies_by_year.keys(), reverse=True)
    verbose(f"Writing {len(all_years)} year pages...", 1)
    for year, year_movies in movies_by_year.items():
        year_movies_sorted = sorted(year_movies,
                                    key=lambda m: (m['title_normalized'] or m['title']).upper())
        shard_dir = os.path.join(targetpath, 'genres', _yshard(year))
        os.makedirs(shard_dir, exist_ok=True)
        _write_year_page(os.path.join(shard_dir, f"{year}.html"), year, year_movies_sorted, poster_uri_map)

    # --- write tag pages ---
    verbose(f"Writing {len(tags_list)} tag pages...", 1)
    for t in tags_list:
        t_movies_sorted = sorted(tags.getMoviesByTagid(db, t['id'], col_where or None),
                                 key=lambda m: m['title'].upper())
        path = os.path.join(targetpath, 'tags', f"{t['oid']}.html")
        _write_tag_page(path, t['tag'], t_movies_sorted, poster_uri_map, movie_by_id)

    # --- build tvstation data and write pages ---
    tvstation_movie_ids = {}  # station_key → set of movie_ids
    for mid, cols in collections_map.items():
        for col in cols:
            if col['tvstation']:
                tvstation_movie_ids.setdefault(col['tvstation'], set()).add(mid)

    tvstations = sorted(tvstation_movie_ids.keys(),
                        key=lambda k: tvstation_module.display_name(k).upper())
    verbose(f"Writing {len(tvstations)} TV station pages...", 1)
    for key in tvstations:
        station_movies = sorted(
            [movie_by_id[mid] for mid in tvstation_movie_ids[key] if mid in movie_by_id],
            key=lambda m: (m['title_normalized'] or m['title']).upper())
        path = os.path.join(targetpath, 'tvstations', f"{key}.html")
        _write_tvstation_page(path, key, station_movies, poster_uri_map)

    # --- build search index ---
    search_index = []
    for m in movies:
        search_index.append({
            'type':    'movie',
            'q':       f"{m['title']} {m['title_orig']}",
            'display': _esc(m['title']),
            'year':    m['year'],
            'url':     f"media/{_pshard(m['oid'])}/{m['oid']}.html",
            'poster':  poster_thumb_map.get(m['id'], ''),
        })
    for a in qualified_actors:
        shard = _pshard(a['oid'])
        search_index.append({
            'type':     'person',
            'q':        a['name'],
            'display':  _esc(a['name']),
            'url':      f"persons/{shard}/{a['oid']}.html",
            'portrait': portrait_thumb_map.get(a['id'], ''),
        })

    # --- write list pages (Neu / Top) ---
    _write_list_page(os.path.join(targetpath, 'new.html'),    'Neu hinzugefügt', newest_250,  poster_uri_map)
    _write_list_page(os.path.join(targetpath, 'top.html'),    'Top bewertet',    top_250,     poster_uri_map)
    _write_list_page(os.path.join(targetpath, 'random.html'), 'Zufall',          random_250,  poster_uri_map, sortable=True, default_sort='title')

    # --- write search.js + index.html ---
    search_index_json = json.dumps(search_index, ensure_ascii=False)
    _write_search_js(targetpath, search_index_json)
    verbose("Writing index.html...", 1)
    _write_index(
        os.path.join(targetpath, 'index.html'),
        targetpath, title,
        newest_movies, top_movies, random_movies,
        top_genres, genre_newest,
        popular_persons, newest_persons, random_persons,
        list(all_genres_dict.values()), tags_list, all_years,
        poster_uri_map, portrait_uri_map,
        tvstations)

    verbose(f"streamer export complete → {targetpath}", 1)
